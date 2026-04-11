from __future__ import annotations

import json
import logging
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from unifoli_api.core.config import get_settings
from unifoli_api.core.llm import GeminiClient, LLMRequestError, OllamaClient, get_llm_client, get_llm_temperature
from unifoli_api.core.security import sanitize_public_error
from unifoli_api.db.models.diagnosis_report_artifact import DiagnosisReportArtifact
from unifoli_api.db.models.diagnosis_run import DiagnosisRun
from unifoli_api.db.models.project import Project
from unifoli_api.schemas.diagnosis import (
    ConsultantDiagnosisArtifactResponse,
    ConsultantDiagnosisEvidenceItem,
    ConsultantDiagnosisReport,
    ConsultantDiagnosisRoadmapItem,
    ConsultantDiagnosisScoreBlock,
    ConsultantDiagnosisScoreGroup,
    ConsultantDiagnosisSection,
    DiagnosisReportMode,
    DiagnosisResultPayload,
)
from unifoli_api.services.document_service import list_documents_for_project
from unifoli_api.services.prompt_registry import (
    PromptAssetNotFoundError,
    PromptRegistryError,
    get_prompt_registry,
)
from unifoli_domain.enums import RenderFormat
from unifoli_render.diagnosis_report_design_contract import get_diagnosis_report_design_contract
from unifoli_render.diagnosis_report_pdf_renderer import render_consultant_diagnosis_pdf
from unifoli_render.template_registry import get_template
from unifoli_shared.storage import get_storage_provider, get_storage_provider_name


logger = logging.getLogger("unifoli.api.diagnosis_report")

_DEFAULT_TEMPLATE_BY_MODE: dict[str, str] = {
    "compact": "consultant_diagnosis_compact",
    "premium_10p": "consultant_diagnosis_premium_10p",
}
_REPORT_FAILURE_FALLBACK = "吏꾨떒 蹂닿퀬???앹꽦???ㅽ뙣?덉뒿?덈떎. ?꾨줈?앺듃 洹쇨굅瑜??뺤씤?????ㅼ떆 ?쒕룄??二쇱꽭??"


class _ConsultantNarrativePayload(BaseModel):
    executive_summary: str = Field(min_length=1, max_length=1600)
    current_record_status_brief: str | None = Field(default=None, max_length=900)
    strengths_brief: str | None = Field(default=None, max_length=900)
    weaknesses_risks_brief: str | None = Field(default=None, max_length=900)
    major_fit_brief: str | None = Field(default=None, max_length=900)
    section_diagnosis_brief: str | None = Field(default=None, max_length=900)
    topic_strategy_brief: str | None = Field(default=None, max_length=900)
    roadmap_bridge: str | None = Field(default=None, max_length=900)
    uncertainty_bridge: str | None = Field(default=None, max_length=900)
    final_consultant_memo: str = Field(min_length=1, max_length=1400)


class _NarrativeGenerationResult(BaseModel):
    narrative: _ConsultantNarrativePayload
    execution_metadata: dict[str, Any] = Field(default_factory=dict)


_PREMIUM_SECTION_ORDER: tuple[str, ...] = (
    "executive_summary",
    "record_baseline_dashboard",
    "narrative_timeline",
    "evidence_cards",
    "strength_analysis",
    "risk_analysis",
    "major_fit",
    "interview_questions",
    "roadmap",
)

_COMPACT_SECTION_ORDER: tuple[str, ...] = (
    "executive_summary",
    "record_baseline_dashboard",
    "strength_analysis",
    "risk_analysis",
    "roadmap",
)


def resolve_consultant_report_template_id(
    *,
    report_mode: DiagnosisReportMode,
    template_id: str | None,
) -> str:
    resolved = (template_id or _DEFAULT_TEMPLATE_BY_MODE[report_mode]).strip()
    # Validate against the registry so frontend always receives a supported template id.
    get_template(resolved, render_format=RenderFormat.PDF)
    return resolved


def get_latest_report_artifact_for_run(
    db: Session,
    *,
    diagnosis_run_id: str,
    report_mode: DiagnosisReportMode | None = None,
) -> DiagnosisReportArtifact | None:
    stmt = select(DiagnosisReportArtifact).where(DiagnosisReportArtifact.diagnosis_run_id == diagnosis_run_id)
    if report_mode is not None:
        stmt = stmt.where(DiagnosisReportArtifact.report_mode == report_mode)
    stmt = stmt.order_by(DiagnosisReportArtifact.version.desc(), DiagnosisReportArtifact.created_at.desc()).limit(1)
    return db.scalar(stmt)


def get_report_artifact_by_id(
    db: Session,
    *,
    diagnosis_run_id: str,
    artifact_id: str,
) -> DiagnosisReportArtifact | None:
    stmt = (
        select(DiagnosisReportArtifact)
        .where(
            DiagnosisReportArtifact.id == artifact_id,
            DiagnosisReportArtifact.diagnosis_run_id == diagnosis_run_id,
        )
        .limit(1)
    )
    return db.scalar(stmt)


def report_artifact_file_path(artifact: DiagnosisReportArtifact) -> Path | str | None:
    if not artifact.generated_file_path:
        return None
    return artifact.generated_file_path


def report_artifact_storage_key(artifact: DiagnosisReportArtifact) -> str | None:
    value = (artifact.storage_key or "").strip()
    if value:
        return value
    legacy = (artifact.generated_file_path or "").strip()
    if not legacy:
        return None
    legacy_path = Path(legacy)
    if legacy_path.is_absolute():
        return None
    return legacy


def report_artifact_execution_metadata(artifact: DiagnosisReportArtifact) -> dict[str, Any] | None:
    raw = (artifact.execution_metadata_json or "").strip()
    if not raw:
        return None
    try:
        decoded = json.loads(raw)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(decoded, dict):
        return decoded
    return None


def load_report_artifact_pdf_bytes(artifact: DiagnosisReportArtifact) -> bytes | None:
    key = report_artifact_storage_key(artifact)
    if not key:
        return None

    storage = get_storage_provider(get_settings())
    if not storage.exists(key):
        return None
    try:
        return storage.retrieve(key)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to retrieve diagnosis report artifact from storage key=%s", key)
        return None


def build_report_artifact_response(
    *,
    artifact: DiagnosisReportArtifact,
    include_payload: bool = True,
) -> ConsultantDiagnosisArtifactResponse:
    settings = get_settings()
    payload = None
    if include_payload and artifact.report_payload_json:
        try:
            payload = ConsultantDiagnosisReport.model_validate_json(artifact.report_payload_json)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to decode diagnosis report payload artifact=%s: %s", artifact.id, exc)

    download_url = None
    if report_artifact_storage_key(artifact):
        download_url = (
            f"{settings.api_prefix}/diagnosis/{artifact.diagnosis_run_id}/report.pdf"
            f"?artifact_id={artifact.id}"
        )
    report_mode = artifact.report_mode if artifact.report_mode in {"compact", "premium_10p"} else "premium_10p"
    report_status = artifact.status if artifact.status in {"READY", "FAILED"} else "FAILED"

    return ConsultantDiagnosisArtifactResponse(
        id=artifact.id,
        diagnosis_run_id=artifact.diagnosis_run_id,
        project_id=artifact.project_id,
        report_mode=report_mode,  # type: ignore[arg-type]
        template_id=artifact.template_id
        or _DEFAULT_TEMPLATE_BY_MODE.get(report_mode, "consultant_diagnosis_premium_10p"),
        export_format="pdf",
        include_appendix=bool(artifact.include_appendix),
        include_citations=bool(artifact.include_citations),
        status=report_status,  # type: ignore[arg-type]
        version=artifact.version,
        storage_provider=artifact.storage_provider,
        storage_key=report_artifact_storage_key(artifact),
        generated_file_path=artifact.generated_file_path,
        download_url=download_url,
        execution_metadata=report_artifact_execution_metadata(artifact),
        error_message=artifact.error_message,
        payload=payload,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


async def generate_consultant_report_artifact(
    db: Session,
    *,
    run: DiagnosisRun,
    project: Project,
    report_mode: DiagnosisReportMode,
    template_id: str | None,
    include_appendix: bool,
    include_citations: bool,
    force_regenerate: bool,
) -> DiagnosisReportArtifact:
    settings = get_settings()
    storage = get_storage_provider(settings)
    resolved_template_id = resolve_consultant_report_template_id(
        report_mode=report_mode,
        template_id=template_id,
    )
    latest_for_mode = get_latest_report_artifact_for_run(
        db,
        diagnosis_run_id=run.id,
        report_mode=report_mode,
    )

    if not force_regenerate and latest_for_mode is not None:
        existing_key = report_artifact_storage_key(latest_for_mode)
        if (
            latest_for_mode.status == "READY"
            and latest_for_mode.template_id == resolved_template_id
            and bool(latest_for_mode.include_appendix) == include_appendix
            and bool(latest_for_mode.include_citations) == include_citations
            and existing_key
            and storage.exists(existing_key)
        ):
            return latest_for_mode

    if not run.result_payload:
        raise ValueError("Diagnosis is not complete yet.")

    result = DiagnosisResultPayload.model_validate_json(run.result_payload)
    documents = list_documents_for_project(db, project.id)
    latest_version = latest_for_mode.version if latest_for_mode is not None else 0
    next_version = latest_version + 1
    started_at = time.perf_counter()

    try:
        report = await build_consultant_report_payload(
            run=run,
            project=project,
            result=result,
            report_mode=report_mode,
            template_id=resolved_template_id,
            include_appendix=include_appendix,
            include_citations=include_citations,
            documents=documents,
        )
        report_json = report.model_dump(mode="json")
        report_json_str = report.model_dump_json()
        execution_metadata_raw = report_json.get("render_hints", {}).get("execution_metadata")
        execution_metadata = execution_metadata_raw if isinstance(execution_metadata_raw, dict) else {}

        stored_path = (
            f"exports/diagnosis_reports/{project.id}/{run.id}/"
            f"consultant-diagnosis-{report_mode}-v{next_version}.pdf"
        )

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            render_consultant_diagnosis_pdf(
                report_payload=report_json,
                output_path=tmp_path,
                report_mode=report_mode,
                template_id=resolved_template_id,
                include_appendix=include_appendix,
                include_citations=include_citations,
            )
            with open(tmp_path, "rb") as f:
                storage.store(f.read(), stored_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        duration_ms = int(max(0.0, (time.perf_counter() - started_at) * 1000.0))
        execution_metadata = {
            **execution_metadata,
            "storage_provider": get_storage_provider_name(storage),
            "storage_key": stored_path,
            "processing_duration_ms": duration_ms,
        }

        artifact = DiagnosisReportArtifact(
            diagnosis_run_id=run.id,
            project_id=project.id,
            report_mode=report_mode,
            template_id=resolved_template_id,
            export_format="pdf",
            include_appendix=include_appendix,
            include_citations=include_citations,
            status="READY",
            version=next_version,
            report_payload_json=report_json_str,
            storage_provider=get_storage_provider_name(storage),
            storage_key=stored_path,
            generated_file_path=stored_path,
            execution_metadata_json=json.dumps(execution_metadata, ensure_ascii=False),
            error_message=None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Consultant diagnosis report generation failed for run=%s", run.id)
        duration_ms = int(max(0.0, (time.perf_counter() - started_at) * 1000.0))
        execution_metadata = {
            "requested_llm_provider": (settings.llm_provider or "gemini").strip().lower(),
            "requested_llm_model": (
                settings.ollama_render_model
                or settings.ollama_model
                or "gemma4"
            ) if (settings.llm_provider or "").strip().lower() == "ollama" else "gemini-1.5-pro",
            "actual_llm_provider": "deterministic_fallback",
            "actual_llm_model": "deterministic_fallback",
            "llm_profile_used": "render",
            "fallback_used": True,
            "fallback_reason": sanitize_public_error(str(exc), fallback=_REPORT_FAILURE_FALLBACK),
            "processing_duration_ms": duration_ms,
        }
        artifact = DiagnosisReportArtifact(
            diagnosis_run_id=run.id,
            project_id=project.id,
            report_mode=report_mode,
            template_id=resolved_template_id,
            export_format="pdf",
            include_appendix=include_appendix,
            include_citations=include_citations,
            status="FAILED",
            version=next_version,
            report_payload_json=_build_failed_report_payload(
                run=run,
                project=project,
                report_mode=report_mode,
                template_id=resolved_template_id,
            ),
            storage_provider=get_storage_provider_name(storage),
            storage_key=None,
            generated_file_path=None,
            execution_metadata_json=json.dumps(execution_metadata, ensure_ascii=False),
            error_message=sanitize_public_error(str(exc), fallback=_REPORT_FAILURE_FALLBACK),
        )

    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


async def build_consultant_report_payload(
    *,
    run: DiagnosisRun,
    project: Project,
    result: DiagnosisResultPayload,
    report_mode: DiagnosisReportMode,
    template_id: str,
    include_appendix: bool,
    include_citations: bool,
    documents: list[Any],
) -> ConsultantDiagnosisReport:
    target_context = _build_target_context(project=project, result=result, documents=documents)
    document_structure = _collect_student_record_structure(documents)
    evidence_bank = _collect_evidence_bank(documents)
    evidence_items = _build_evidence_items(result)
    score_groups = _build_score_groups(
        result=result,
        document_structure=document_structure,
        evidence_items=evidence_items,
        evidence_bank=evidence_bank,
    )
    student_score_group = next((group for group in score_groups if group.group == "student_evaluation"), None)
    system_score_group = next((group for group in score_groups if group.group == "system_quality"), None)
    score_blocks = list(student_score_group.blocks) if student_score_group else []
    contradiction_blocked = bool(system_score_group and system_score_group.gating_status == "blocked")
    unique_anchor_ids = {
        str(item.get("anchor_id") or "").strip()
        for item in evidence_bank
        if str(item.get("anchor_id") or "").strip()
    }
    unique_anchor_pages = {
        int(item.get("page") or 0)
        for item in evidence_bank
        if int(item.get("page") or 0) > 0
    }
    evidence_anchor_gate_failed = len(unique_anchor_ids) < 10 or len(unique_anchor_pages) < 6
    reanalysis_required = bool(
        (student_score_group and student_score_group.gating_status == "reanalysis_required")
        or (system_score_group and system_score_group.gating_status == "reanalysis_required")
        or evidence_anchor_gate_failed
    )
    if evidence_anchor_gate_failed:
        for group in score_groups:
            if group.gating_status != "blocked":
                group.gating_status = "reanalysis_required"
                message = f"怨좎쑀 ?듭빱 {len(unique_anchor_ids)}媛?/ ?섏씠吏 {len(unique_anchor_pages)}媛쒕줈 ?덉쭏 寃뚯씠??誘몄땐議?
                group.note = _clean_line(f"{group.note or ''} {message}".strip(), max_len=220)
    if contradiction_blocked:
        raise ValueError("contradiction_check_failed")
    uncertainty_notes = _build_uncertainty_notes(
        result=result,
        document_structure=document_structure,
        evidence_items=evidence_items,
    )
    if reanalysis_required:
        uncertainty_notes = _dedupe(
            [
                "?щ텇???꾩슂: ?꾩닔 ?뱀뀡 而ㅻ쾭由ъ?媛 遺議깊븯嫄곕굹 洹쇨굅 ?듭빱 遺꾩궛????뒿?덈떎.",
                (
                    f"?듭빱 ?덉쭏 寃뚯씠??誘몄땐議? 怨좎쑀 ?듭빱 {len(unique_anchor_ids)}媛?/ 怨좎쑀 ?섏씠吏 {len(unique_anchor_pages)}媛?
                    if evidence_anchor_gate_failed
                    else ""
                ),
                *uncertainty_notes,
            ],
            limit=10,
        )
    roadmap = _build_roadmap(result=result, uncertainty_notes=uncertainty_notes)
    narratives_result_raw = await _generate_narratives(
        project=project,
        result=result,
        document_structure=document_structure,
        uncertainty_notes=uncertainty_notes,
    )
    if isinstance(narratives_result_raw, _NarrativeGenerationResult):
        narratives_result = narratives_result_raw
    else:
        narratives_result = _NarrativeGenerationResult(
            narrative=_ConsultantNarrativePayload.model_validate(narratives_result_raw),
            execution_metadata={
                "requested_llm_provider": None,
                "requested_llm_model": None,
                "actual_llm_provider": None,
                "actual_llm_model": None,
                "llm_profile_used": "render",
                "fallback_used": None,
                "fallback_reason": None,
            },
        )
    narratives = _enforce_narrative_contract(
        narratives_result.narrative,
        result=result,
        document_structure=document_structure,
        uncertainty_notes=uncertainty_notes,
    )
    template = get_template(template_id, render_format=RenderFormat.PDF)
    design_contract = get_diagnosis_report_design_contract(
        report_mode=report_mode,
        template_id=template_id,
        template_section_schema=template.section_schema,
    )

    sections = _build_sections(
        result=result,
        report_mode=report_mode,
        target_context=target_context,
        evidence_items=evidence_items,
        score_groups=score_groups,
        document_structure=document_structure,
        evidence_bank=evidence_bank,
        roadmap=roadmap,
        narratives=narratives,
        uncertainty_notes=uncertainty_notes,
        reanalysis_required=reanalysis_required,
    )
    sections = _enforce_section_architecture(sections, report_mode=report_mode)

    appendix_notes: list[str] = []
    internal_qa_artifact = _build_appendix_notes(documents, document_structure)
    if include_appendix and report_mode == "compact":
        appendix_notes.extend(internal_qa_artifact)
    if include_citations and report_mode == "compact":
        appendix_notes.append("?몄슜 遺濡앹뿉??二쇱옣-洹쇨굅 ?곌껐 寃利앹쓣 ?꾪븳 異쒖쿂 ?쇱씤???ы븿?⑸땲??")

    report_payload = ConsultantDiagnosisReport(
        diagnosis_run_id=run.id,
        project_id=project.id,
        report_mode=report_mode,
        template_id=template_id,
        title=f"{project.title} ?꾨Ц 而⑥꽕?댄듃 吏꾨떒??,
        subtitle="?숈깮遺 洹쇨굅 湲곕컲 吏꾨떒 쨌 由ъ뒪??紐낆떆 쨌 ?ㅽ뻾 濡쒕뱶留?,
        student_target_context=target_context,
        generated_at=datetime.now(timezone.utc),
        score_blocks=score_blocks,
        score_groups=score_groups,
        sections=sections,
        roadmap=roadmap,
        citations=evidence_items if include_citations and report_mode == "compact" else [],
        uncertainty_notes=uncertainty_notes,
        final_consultant_memo=narratives.final_consultant_memo,
        appendix_notes=appendix_notes,
        render_hints={
            "a4": True,
            "minimum_pages": 10 if report_mode == "premium_10p" else 5,
            "visual_tone": "consultant_premium",
            "include_appendix": include_appendix,
            "include_citations": include_citations,
            "analysis_confidence_score": float(
                ((document_structure.get("coverage_check") or {}).get("coverage_score", 0.0))
                if isinstance(document_structure.get("coverage_check"), dict)
                else 0.0
            ),
            "one_line_verdict": _clean_line(narratives.executive_summary, max_len=150),
            "public_appendix_enabled": bool(include_appendix and report_mode == "compact"),
            "public_citations_enabled": bool(include_citations and report_mode == "compact"),
            "section_order": list(_PREMIUM_SECTION_ORDER if report_mode == "premium_10p" else _COMPACT_SECTION_ORDER),
            "design_contract": design_contract,
            "internal_qa_artifact": {
                "appendix_notes": internal_qa_artifact,
                "evidence_bank_size": len(evidence_bank),
                "unique_evidence_pages": len({int(item.get("page") or 0) for item in evidence_bank if int(item.get("page") or 0) > 0}),
                "reanalysis_required": reanalysis_required,
            },
            "execution_metadata": {
                **narratives_result.execution_metadata,
                "diagnosis_backbone_requested_llm_provider": result.requested_llm_provider,
                "diagnosis_backbone_requested_llm_model": result.requested_llm_model,
                "diagnosis_backbone_actual_llm_provider": result.actual_llm_provider,
                "diagnosis_backbone_actual_llm_model": result.actual_llm_model,
                "diagnosis_backbone_fallback_used": result.fallback_used,
                "diagnosis_backbone_fallback_reason": result.fallback_reason,
                "reanalysis_required": reanalysis_required,
            },
        },
    )
    return report_payload


def _build_target_context(*, project: Project, result: DiagnosisResultPayload, documents: list[Any]) -> str:
    target_university = project.target_university or "誘몄꽕??
    target_major = project.target_major or "誘몄꽕??
    diagnosis_target = result.diagnosis_summary.target_context if result.diagnosis_summary else None
    student_name = "誘명솗??
    for document in documents:
        metadata = getattr(document, "parse_metadata", None)
        if not isinstance(metadata, dict):
            continue
        canonical = metadata.get("student_record_canonical")
        if isinstance(canonical, dict):
            analysis_artifact = metadata.get("analysis_artifact")
            canonical_data = (
                analysis_artifact.get("canonical_data")
                if isinstance(analysis_artifact, dict) and isinstance(analysis_artifact.get("canonical_data"), dict)
                else {}
            )
            candidate = str(canonical_data.get("student_name") or "").strip()
            if candidate:
                student_name = candidate
                break
    context_bits = [
        f"?숈깮: {student_name}",
        f"?꾨줈?앺듃: {project.title}",
        f"紐⑺몴 ??? {target_university}",
        f"紐⑺몴 ?꾧났: {target_major}",
        f"遺꾩꽍 臾몄꽌 ?? {len(documents)}",
    ]
    if diagnosis_target:
        context_bits.append(f"吏꾨떒 ?源?硫붾え: {diagnosis_target}")
    return " | ".join(context_bits)


def _build_score_blocks(*, result: DiagnosisResultPayload) -> list[ConsultantDiagnosisScoreBlock]:
    blocks: list[ConsultantDiagnosisScoreBlock] = []
    for axis in result.admission_axes or []:
        blocks.append(
            ConsultantDiagnosisScoreBlock(
                key=axis.key,
                label=axis.label,
                score=int(axis.score),
                band=axis.band,
                interpretation=axis.rationale,
                uncertainty_note="?대떦 ?먯닔???낅젰 臾몄꽌 湲곕컲 ?곷??됯??대ŉ ?덈? ?⑷꺽?덉륫???꾨떂.",
            )
        )

    if not blocks:
        blocks.append(
            ConsultantDiagnosisScoreBlock(
                key="fallback",
                label="吏꾨떒 ?붿빟 ?먯닔",
                score=52,
                band="watch",
                interpretation="援ъ“???먯닔 異뺤씠 遺議깊븯??蹂댁닔??湲곕낯 ?먯닔瑜??ъ슜?덉뒿?덈떎.",
                uncertainty_note="異붽? 臾몄꽌 洹쇨굅 ?뺣낫 ???ъ깮??沅뚯옣.",
            )
        )
    return blocks


def _build_evidence_items(result: DiagnosisResultPayload) -> list[ConsultantDiagnosisEvidenceItem]:
    evidence_items: list[ConsultantDiagnosisEvidenceItem] = []
    for citation in result.citations or []:
        score = float(citation.relevance_score)
        if score >= 1.6:
            support_status = "verified"
        elif score >= 0.8:
            support_status = "probable"
        else:
            support_status = "needs_verification"
        evidence_items.append(
            ConsultantDiagnosisEvidenceItem(
                source_label=citation.source_label,
                page_number=citation.page_number,
                excerpt=citation.excerpt,
                relevance_score=round(score, 3),
                support_status=support_status,
            )
        )
    return evidence_items[:40]


def _collect_evidence_bank(documents: list[Any]) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for document in documents:
        metadata = getattr(document, "parse_metadata", None)
        if not isinstance(metadata, dict):
            continue
        canonical = metadata.get("student_record_canonical")
        if not isinstance(canonical, dict):
            continue
        raw_bank = canonical.get("evidence_bank")
        if not isinstance(raw_bank, list):
            continue
        for item in raw_bank:
            if not isinstance(item, dict):
                continue
            try:
                page = int(item.get("page") or 0)
            except (TypeError, ValueError):
                continue
            quote = str(item.get("quote") or "").strip()
            if page <= 0 or not quote:
                continue
            dedupe_key = (page, quote)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            collected.append(item)
    return collected


def _build_score_groups(
    *,
    result: DiagnosisResultPayload,
    document_structure: dict[str, Any],
    evidence_items: list[ConsultantDiagnosisEvidenceItem],
    evidence_bank: list[dict[str, Any]],
) -> list[ConsultantDiagnosisScoreGroup]:
    section_density = (
        document_structure.get("section_density")
        if isinstance(document_structure.get("section_density"), dict)
        else {}
    )
    coverage_check = (
        document_structure.get("coverage_check")
        if isinstance(document_structure.get("coverage_check"), dict)
        else {}
    )
    contradiction_check = (
        document_structure.get("contradiction_check")
        if isinstance(document_structure.get("contradiction_check"), dict)
        else {"passed": True, "items": []}
    )
    parse_coverage_score = int(round(float(coverage_check.get("coverage_score", 0.0)) * 100))
    major_fit_seed = _axis_score(result=result, key="major_alignment", fallback=58)
    continuity_seed = _axis_score(result=result, key="inquiry_continuity", fallback=55)
    density_seed = _axis_score(result=result, key="evidence_density", fallback=52)
    process_seed = _axis_score(result=result, key="process_explanation", fallback=54)

    design_signal = _count_keywords(
        evidence_bank,
        keywords=("嫄댁텞", "怨듦컙", "援ъ“", "?щ즺", "?섍꼍", "湲고썑", "?щ궃", "?ㅺ퀎"),
    )
    ux_humanities_signal = _count_keywords(
        evidence_bank,
        keywords=("?ъ슜??, "寃쏀뿕", "?숈꽑", "怨듦났??, "?몃Ц", "?ы쉶臾명솕"),
    )
    design_spatial_score = max(38, min(95, 50 + design_signal * 3 - max(0, 2 - ux_humanities_signal) * 4))
    academic_base_score = max(
        35,
        min(
            95,
            int(round((float(section_density.get("援먭낵?숈뒿諛쒕떖?곹솴", 0.0)) * 55) + (major_fit_seed * 0.45))),
        ),
    )
    leadership_score = max(
        34,
        min(
            92,
            int(
                round(
                    (float(section_density.get("李쎌껜", 0.0)) * 45)
                    + (float(section_density.get("?됰룞?뱀꽦", 0.0)) * 35)
                    + 18
                )
            ),
        ),
    )

    student_specs: list[tuple[str, str, int, str]] = [
        ("major_fit", "?꾧났 ?곹빀??, major_fit_seed, "嫄댁텞 ?꾧났 ?곌퀎 洹쇨굅??吏곸젒?깃낵 ?곗냽??),
        ("inquiry_depth", "?먭뎄 源딆씠", int(round((process_seed * 0.5) + (density_seed * 0.5))), "臾몄젣?ㅼ젙-諛⑸쾿-寃곌낵-?뺤옣??源딆씠"),
        ("inquiry_continuity", "?먭뎄 ?곗냽??, continuity_seed, "?숇뀈 媛?二쇱젣???곗냽?깃낵 ?ы솕 ?먮쫫"),
        ("evidence_density", "洹쇨굅 諛??, density_seed, "二쇱옣 ?鍮??먮Ц 洹쇨굅 ?듭빱??諛??),
        ("process_explanation", "怨쇱젙 ?ㅻ챸??, process_seed, "怨쇱젙쨌諛⑸쾿쨌?쒓퀎쨌媛쒖꽑???ㅻ챸 異⑹떎??),
        ("design_spatial_thinking", "?ㅺ퀎쨌怨듦컙 ?ш퀬", int(design_spatial_score), "援ъ“쨌?щ즺쨌?섍꼍 以묒떖 ?ㅺ퀎 ?ш퀬"),
        ("academic_base", "?숈뾽 湲곕컲", int(academic_base_score), "援먭낵 ?깆랬? ?명듅 洹쇨굅???덉젙??),
        ("leadership_collaboration", "由щ뜑??룻삊??, int(leadership_score), "?묒뾽쨌怨듬룞泥는룹콉???좏샇"),
    ]

    student_blocks: list[ConsultantDiagnosisScoreBlock] = []
    for key, label, raw_score, interpretation in student_specs:
        score = max(0, min(100, int(raw_score)))
        anchor_ids = _select_anchor_ids_for_score(key=key, evidence_bank=evidence_bank)
        if len(anchor_ids) < 2:
            score = min(score, 45)
            uncertainty = "怨좎쑀 洹쇨굅 ?듭빱媛 2媛?誘몃쭔?대씪 ?щ텇?????ы룊媛媛 ?꾩슂?⑸땲??"
        else:
            uncertainty = f"怨좎쑀 洹쇨굅 ?듭빱 {len(anchor_ids)}媛??뺤씤"
        student_blocks.append(
            ConsultantDiagnosisScoreBlock(
                key=key,
                label=label,
                score=score,
                band="high" if score >= 75 else "mid" if score >= 50 else "low",
                interpretation=interpretation,
                uncertainty_note=uncertainty,
            )
        )

    unique_citation_pages = len({item.page_number for item in evidence_items if item.page_number})
    citation_coverage_score = min(100, int(round((unique_citation_pages / max(len(evidence_items), 1)) * 100)))
    unique_quotes = {str(item.get("quote") or "").strip() for item in evidence_bank if str(item.get("quote") or "").strip()}
    evidence_uniqueness_score = min(100, int(round((len(unique_quotes) / max(len(evidence_bank), 1)) * 100)))
    redaction_safety_score = 100 if _redaction_safety_ok(evidence_bank) else 55
    contradiction_passed = bool(contradiction_check.get("passed", True))
    contradiction_score = 100 if contradiction_passed else 0

    system_blocks = [
        ConsultantDiagnosisScoreBlock(
            key="parse_coverage",
            label="?뚯떛 而ㅻ쾭由ъ?",
            score=max(0, min(100, parse_coverage_score)),
            band="high" if parse_coverage_score >= 80 else "mid" if parse_coverage_score >= 60 else "low",
            interpretation="?꾩닔 ?뺢퇋???뱀뀡 異붿텧 而ㅻ쾭由ъ?",
            uncertainty_note=None,
        ),
        ConsultantDiagnosisScoreBlock(
            key="citation_coverage",
            label="?몄슜 而ㅻ쾭由ъ?",
            score=citation_coverage_score,
            band="high" if citation_coverage_score >= 65 else "mid" if citation_coverage_score >= 35 else "low",
            interpretation="洹쇨굅 ?섏씠吏 遺꾩궛怨??몄슜 ?곌껐??,
            uncertainty_note=None,
        ),
        ConsultantDiagnosisScoreBlock(
            key="evidence_uniqueness",
            label="洹쇨굅 怨좎쑀??,
            score=evidence_uniqueness_score,
            band="high" if evidence_uniqueness_score >= 75 else "mid" if evidence_uniqueness_score >= 50 else "low",
            interpretation="以묐났 ?몄슜 怨쇰떎 ?щ?",
            uncertainty_note=None,
        ),
        ConsultantDiagnosisScoreBlock(
            key="contradiction_check",
            label="紐⑥닚 寃利?,
            score=contradiction_score,
            band="high" if contradiction_passed else "low",
            interpretation="?뱀뀡 ?꾨씫/諛???곹깭 紐⑥닚 寃利?,
            uncertainty_note=None if contradiction_passed else "紐⑥닚??媛먯??섏뼱 ?꾨━誘몄뾼 ?뚮뜑瑜?李⑤떒?⑸땲??",
        ),
        ConsultantDiagnosisScoreBlock(
            key="redaction_safety",
            label="鍮꾩떇蹂??덉쟾??,
            score=redaction_safety_score,
            band="high" if redaction_safety_score >= 80 else "low",
            interpretation="誘쇨컧?뺣낫 ?몄텧 ?꾪뿕 ?먭?",
            uncertainty_note=None if redaction_safety_score >= 80 else "誘쇨컧?뺣낫 ?⑦꽩??媛먯??섏뼱 寃?좉? ?꾩슂?⑸땲??",
        ),
    ]

    reanalysis_required = bool(coverage_check.get("reanalysis_required")) or parse_coverage_score < 70
    student_group = ConsultantDiagnosisScoreGroup(
        group="student_evaluation",
        title="?숈깮 ?됯? ?먯닔",
        blocks=student_blocks,
        gating_status="reanalysis_required" if reanalysis_required else "ok",
        note=(
            "?뚯떛 而ㅻ쾭由ъ?媛 ??븘 ?숈깮 ?먯닔??李멸퀬?⑹쑝濡쒕쭔 ?쒖떆?⑸땲??"
            if reanalysis_required
            else "紐⑤뱺 ?먯닔??理쒖냼 2媛??댁긽??怨좎쑀 洹쇨굅 ?듭빱瑜?湲곗??쇰줈 ?곗텧?섏뿀?듬땲??"
        ),
    )
    system_group = ConsultantDiagnosisScoreGroup(
        group="system_quality",
        title="?쒖뒪???덉쭏 ?먯닔",
        blocks=system_blocks,
        gating_status="blocked" if not contradiction_passed else ("reanalysis_required" if reanalysis_required else "ok"),
        note=(
            "紐⑥닚 寃利??ㅽ뙣濡??꾨━誘몄뾼 PDF ?뚮뜑瑜?以묐떒?⑸땲??"
            if not contradiction_passed
            else "?쒖뒪???덉쭏 ?먯닔???숈깮 ?됯? ?먯닔? 遺꾨━?섏뼱 ?댁꽍?⑸땲??"
        ),
    )
    return [student_group, system_group]


def _axis_score(*, result: DiagnosisResultPayload, key: str, fallback: int) -> int:
    for axis in result.admission_axes or []:
        if axis.key == key:
            return int(max(0, min(100, axis.score)))
    return fallback


def _count_keywords(evidence_bank: list[dict[str, Any]], *, keywords: tuple[str, ...]) -> int:
    count = 0
    for item in evidence_bank:
        quote = str(item.get("quote") or "")
        if any(keyword in quote for keyword in keywords):
            count += 1
    return count


def _select_anchor_ids_for_score(*, key: str, evidence_bank: list[dict[str, Any]]) -> list[str]:
    keyword_map: dict[str, tuple[str, ...]] = {
        "major_fit": ("嫄댁텞", "?꾧났", "吏꾨줈", "?ㅺ퀎", "?섍꼍", "援ъ“"),
        "inquiry_depth": ("?먭뎄", "?ㅽ뿕", "媛??, "遺꾩꽍", "鍮꾧탳"),
        "inquiry_continuity": ("?ы솕", "?뺤옣", "?꾩냽", "?곌퀎", "吏??),
        "evidence_density": ("寃곌낵", "?섏튂", "吏??, "洹쇨굅"),
        "process_explanation": ("怨쇱젙", "諛⑸쾿", "?쒓퀎", "媛쒖꽑"),
        "design_spatial_thinking": ("?ㅺ퀎", "怨듦컙", "援ъ“", "?щ즺", "嫄댁텞"),
        "academic_base": ("援먭낵", "?깆랬", "?명듅", "怨쇰ぉ"),
        "leadership_collaboration": ("?묒뾽", "怨듬룞泥?, "由щ뜑", "遊됱궗"),
    }
    keywords = keyword_map.get(key, ())
    selected: list[str] = []
    for item in evidence_bank:
        quote = str(item.get("quote") or "")
        if keywords and not any(keyword in quote for keyword in keywords):
            continue
        anchor_id = str(item.get("anchor_id") or "").strip()
        if anchor_id and anchor_id not in selected:
            selected.append(anchor_id)
        if len(selected) >= 4:
            break
    if len(selected) >= 2:
        return selected

    for item in evidence_bank:
        anchor_id = str(item.get("anchor_id") or "").strip()
        if anchor_id and anchor_id not in selected:
            selected.append(anchor_id)
        if len(selected) >= 2:
            break
    return selected


def _redaction_safety_ok(evidence_bank: list[dict[str, Any]]) -> bool:
    pii_patterns = (
        re.compile(r"\b01[0-9][- ]?\d{3,4}[- ]?\d{4}\b"),
        re.compile(r"\b\d{6}[- ]?\d{7}\b"),
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    )
    for item in evidence_bank:
        quote = str(item.get("quote") or "")
        if any(pattern.search(quote) for pattern in pii_patterns):
            return False
    return True


def _collect_student_record_structure(documents: list[Any]) -> dict[str, Any]:
    section_density: dict[str, float] = {}
    weak_sections: list[str] = []
    timeline_signals: list[str] = []
    activity_clusters: list[str] = []
    alignment_signals: list[str] = []
    continuity_signals: list[str] = []
    process_signals: list[str] = []
    uncertain_items: list[str] = []
    coverage_check: dict[str, Any] = {
        "required_sections": [],
        "missing_required_sections": [],
        "coverage_score": 0.0,
        "reanalysis_required": False,
    }
    contradiction_check: dict[str, Any] = {"passed": True, "items": []}

    for document in documents:
        metadata = getattr(document, "parse_metadata", None)
        if not isinstance(metadata, dict):
            continue
        canonical = metadata.get("student_record_canonical")
        if isinstance(canonical, dict):
            timeline_signals.extend(_extract_canonical_values(canonical.get("timeline_signals"), "signal"))
            alignment_signals.extend(_extract_canonical_values(canonical.get("major_alignment_hints"), "hint"))
            weak_sections.extend(_extract_canonical_values(canonical.get("weak_or_missing_sections"), "section"))
            uncertain_items.extend(_extract_canonical_values(canonical.get("uncertainties"), "message"))
            activity_clusters.extend(_extract_canonical_values(canonical.get("extracurricular"), "label"))
            process_signals.extend(_extract_canonical_values(canonical.get("subject_special_notes"), "label"))
            career_signals = _extract_canonical_values(canonical.get("career_signals"), "label")
            continuity_signals.extend(career_signals)
            canonical_coverage = canonical.get("section_coverage")
            if isinstance(canonical_coverage, dict):
                coverage_check = {
                    "required_sections": list(canonical_coverage.get("section_counts", {}).keys())
                    if isinstance(canonical_coverage.get("section_counts"), dict)
                    else coverage_check.get("required_sections", []),
                    "missing_required_sections": list(canonical_coverage.get("missing_sections", []))
                    if isinstance(canonical_coverage.get("missing_sections"), list)
                    else coverage_check.get("missing_required_sections", []),
                    "coverage_score": max(
                        float(coverage_check.get("coverage_score", 0.0)),
                        float(canonical_coverage.get("coverage_score", 0.0) or 0.0),
                    ),
                    "reanalysis_required": bool(canonical_coverage.get("reanalysis_required"))
                    or bool(coverage_check.get("reanalysis_required")),
                }
            quality_gates = canonical.get("quality_gates")
            if isinstance(quality_gates, dict):
                if quality_gates.get("reanalysis_required"):
                    coverage_check["reanalysis_required"] = True
                missing_required = quality_gates.get("missing_required_sections")
                if isinstance(missing_required, list):
                    merged_missing = _dedupe(
                        [
                            *[str(item) for item in coverage_check.get("missing_required_sections", [])],
                            *[str(item) for item in missing_required],
                        ],
                        limit=20,
                    )
                    coverage_check["missing_required_sections"] = merged_missing

            section_classification = canonical.get("section_classification")
            if isinstance(section_classification, dict):
                for legacy_key, canonical_key in (
                    ("援먭낵?숈뒿諛쒕떖?곹솴", "grades_subjects"),
                    ("?명듅", "subject_special_notes"),
                    ("李쎌껜", "extracurricular"),
                    ("吏꾨줈", "career_signals"),
                    ("?낆꽌", "reading_activity"),
                    ("?됰룞?뱀꽦", "behavior_opinion"),
                ):
                    payload = section_classification.get(canonical_key)
                    if not isinstance(payload, dict):
                        continue
                    try:
                        normalized = max(0.0, min(1.0, float(payload.get("density") or 0.0)))
                    except (TypeError, ValueError):
                        continue
                    section_density[legacy_key] = max(section_density.get(legacy_key, 0.0), normalized)
        structure_candidates = _extract_structure_candidates(metadata)

        for structure in structure_candidates:
            for key, value in (structure.get("section_density") or {}).items():
                try:
                    normalized = max(0.0, min(1.0, float(value)))
                except (TypeError, ValueError):
                    continue
                section_density[str(key)] = max(section_density.get(str(key), 0.0), normalized)

            weak_sections.extend([str(item).strip() for item in structure.get("weak_sections", []) if str(item).strip()])
            timeline_signals.extend([str(item).strip() for item in structure.get("timeline_signals", []) if str(item).strip()])
            activity_clusters.extend([str(item).strip() for item in structure.get("activity_clusters", []) if str(item).strip()])
            alignment_signals.extend([str(item).strip() for item in structure.get("subject_major_alignment_signals", []) if str(item).strip()])
            continuity_signals.extend([str(item).strip() for item in structure.get("continuity_signals", []) if str(item).strip()])
            process_signals.extend([str(item).strip() for item in structure.get("process_reflection_signals", []) if str(item).strip()])
            uncertain_items.extend([str(item).strip() for item in structure.get("uncertain_items", []) if str(item).strip()])
            coverage_candidate = structure.get("coverage_check")
            if isinstance(coverage_candidate, dict):
                coverage_check["coverage_score"] = max(
                    float(coverage_check.get("coverage_score", 0.0)),
                    float(coverage_candidate.get("coverage_score", 0.0) or 0.0),
                )
                if bool(coverage_candidate.get("reanalysis_required")):
                    coverage_check["reanalysis_required"] = True
                if isinstance(coverage_candidate.get("required_sections"), list):
                    coverage_check["required_sections"] = _dedupe(
                        [*coverage_check.get("required_sections", []), *coverage_candidate.get("required_sections", [])],
                        limit=30,
                    )
                if isinstance(coverage_candidate.get("missing_required_sections"), list):
                    coverage_check["missing_required_sections"] = _dedupe(
                        [*coverage_check.get("missing_required_sections", []), *coverage_candidate.get("missing_required_sections", [])],
                        limit=30,
                    )
            contradiction_candidate = structure.get("contradiction_check")
            if isinstance(contradiction_candidate, dict):
                contradiction_check["passed"] = bool(contradiction_candidate.get("passed", True)) and bool(
                    contradiction_check.get("passed", True)
                )
                candidate_items = contradiction_candidate.get("items")
                if isinstance(candidate_items, list):
                    contradiction_check["items"] = [*contradiction_check.get("items", []), *candidate_items]

        pdf_analysis = metadata.get("pdf_analysis")
        if isinstance(pdf_analysis, dict):
            uncertain_items.extend([str(item).strip() for item in pdf_analysis.get("evidence_gaps", []) if str(item).strip()])

    normalized_weak_sections = _dedupe([_normalize_section_name(str(item)) for item in weak_sections], limit=20)
    filtered_weak_sections: list[str] = []
    contradiction_items: list[dict[str, Any]] = list(contradiction_check.get("items", []))
    for section in normalized_weak_sections:
        density = float(section_density.get(section, 0.0))
        if density >= 0.95:
            contradiction_items.append(
                {
                    "section": section,
                    "density": round(density, 3),
                    "reason": "weak_or_missing_conflicts_with_density",
                }
            )
            continue
        filtered_weak_sections.append(section)
    contradiction_check["items"] = contradiction_items
    contradiction_check["passed"] = bool(contradiction_check.get("passed", True)) and len(contradiction_items) == 0

    return {
        "section_density": section_density,
        "weak_sections": _dedupe(filtered_weak_sections, limit=12),
        "timeline_signals": _dedupe(timeline_signals, limit=12),
        "activity_clusters": _dedupe(activity_clusters, limit=12),
        "subject_major_alignment_signals": _dedupe(alignment_signals, limit=12),
        "continuity_signals": _dedupe(continuity_signals, limit=10),
        "process_reflection_signals": _dedupe(process_signals, limit=10),
        "uncertain_items": _dedupe(uncertain_items, limit=12),
        "coverage_check": coverage_check,
        "contradiction_check": contradiction_check,
    }


def _extract_structure_candidates(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    canonical = metadata.get("student_record_canonical")
    if isinstance(canonical, dict):
        converted = _canonical_to_structure_candidate(canonical)
        if converted:
            candidates.append(converted)

    direct = metadata.get("student_record_structure")
    if isinstance(direct, dict):
        candidates.append(direct)

    analysis_artifact = metadata.get("analysis_artifact")
    if isinstance(analysis_artifact, dict):
        nested = analysis_artifact.get("student_record_structure")
        if isinstance(nested, dict):
            candidates.append(nested)
        fallback = analysis_artifact.get("structure")
        if isinstance(fallback, dict):
            candidates.append(fallback)

    return candidates


def _canonical_to_structure_candidate(canonical: dict[str, Any]) -> dict[str, Any]:
    section_classification = canonical.get("section_classification")
    section_density: dict[str, float] = {}
    if isinstance(section_classification, dict):
        for legacy_key, canonical_key in (
            ("援먭낵?숈뒿諛쒕떖?곹솴", "grades_subjects"),
            ("?명듅", "subject_special_notes"),
            ("李쎌껜", "extracurricular"),
            ("吏꾨줈", "career_signals"),
            ("?낆꽌", "reading_activity"),
            ("?됰룞?뱀꽦", "behavior_opinion"),
        ):
            payload = section_classification.get(canonical_key)
            if not isinstance(payload, dict):
                continue
            try:
                density = max(0.0, min(1.0, float(payload.get("density") or 0.0)))
            except (TypeError, ValueError):
                continue
            section_density[legacy_key] = density

    return {
        "section_density": section_density,
        "weak_sections": _extract_canonical_values(canonical.get("weak_or_missing_sections"), "section"),
        "timeline_signals": _extract_canonical_values(canonical.get("timeline_signals"), "signal"),
        "activity_clusters": _extract_canonical_values(canonical.get("extracurricular"), "label"),
        "subject_major_alignment_signals": _extract_canonical_values(canonical.get("major_alignment_hints"), "hint"),
        "continuity_signals": _extract_canonical_values(canonical.get("career_signals"), "label"),
        "process_reflection_signals": _extract_canonical_values(canonical.get("subject_special_notes"), "label"),
        "uncertain_items": _extract_canonical_values(canonical.get("uncertainties"), "message"),
        "coverage_check": {
            "required_sections": list((canonical.get("section_coverage") or {}).get("section_counts", {}).keys())
            if isinstance((canonical.get("section_coverage") or {}).get("section_counts"), dict)
            else [],
            "missing_required_sections": list((canonical.get("quality_gates") or {}).get("missing_required_sections", []))
            if isinstance((canonical.get("quality_gates") or {}).get("missing_required_sections"), list)
            else list((canonical.get("section_coverage") or {}).get("missing_sections", []))
            if isinstance((canonical.get("section_coverage") or {}).get("missing_sections"), list)
            else [],
            "coverage_score": float((canonical.get("section_coverage") or {}).get("coverage_score", 0.0) or 0.0),
            "reanalysis_required": bool((canonical.get("quality_gates") or {}).get("reanalysis_required"))
            or bool((canonical.get("section_coverage") or {}).get("reanalysis_required")),
        },
        "contradiction_check": {
            "passed": True,
            "items": [],
        },
    }


def _extract_canonical_values(values: Any, key: str) -> list[str]:
    if not isinstance(values, list):
        return []
    output: list[str] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        value = str(item.get(key) or "").strip()
        if value:
            output.append(value)
    return output


def _build_uncertainty_notes(
    *,
    result: DiagnosisResultPayload,
    document_structure: dict[str, Any],
    evidence_items: list[ConsultantDiagnosisEvidenceItem],
) -> list[str]:
    notes: list[str] = []
    coverage_check = (
        document_structure.get("coverage_check")
        if isinstance(document_structure.get("coverage_check"), dict)
        else {}
    )
    contradiction_check = (
        document_structure.get("contradiction_check")
        if isinstance(document_structure.get("contradiction_check"), dict)
        else {"passed": True, "items": []}
    )
    if result.document_quality and result.document_quality.needs_review:
        notes.append("臾몄꽌 ?뚯떛 ?덉쭏 ?먭? ?꾩슂: ?쇰? ?섏씠吏/援ъ뿭? ?섎룞 寃?????뺤젙?댁빞 ?⑸땲??")
    if not evidence_items:
        notes.append("吏곸젒 ?몄슜 媛?ν븳 洹쇨굅媛 遺議깊빀?덈떎. 二쇱슂 二쇱옣留덈떎 ?먮Ц 異쒖쿂瑜?蹂닿컯?섏꽭??")
    if result.review_required:
        notes.append("?뺤콉/?덉쟾 ?뚮옒洹멸? 媛먯??섏뼱 寃???쒖뒪?ш? ?대┛ ?곹깭?낅땲??")
    if bool(coverage_check.get("reanalysis_required")):
        missing = coverage_check.get("missing_required_sections")
        if isinstance(missing, list) and missing:
            notes.append(f"?꾩닔 ?뱀뀡 ?꾨씫: {', '.join(str(item) for item in missing[:6])}")
        else:
            notes.append("?꾩닔 ?뱀뀡 而ㅻ쾭由ъ?媛 ??븘 ?щ텇?앹씠 ?꾩슂?⑸땲??")
    if not bool(contradiction_check.get("passed", True)):
        notes.append("紐⑥닚 寃利??ㅽ뙣: ?꾨씫 ?곹깭? 諛???곹깭媛 異⑸룎?섏뿬 ?꾨━誘몄뾼 ?뚮뜑瑜?李⑤떒?⑸땲??")
    for item in document_structure.get("uncertain_items", [])[:4]:
        notes.append(f"援ъ“ 異붿젙 遺덊솗?? {item}")
    if not notes:
        notes.append("?꾩옱 洹쇨굅 踰붿쐞 ?댁뿉??蹂댁닔?곸쑝濡??댁꽍?덉뒿?덈떎. ?덈줈???깆랬 ?쒖닠? 異붽? 寃利???諛섏쁺?섏꽭??")
    return _dedupe(notes, limit=8)


def _build_roadmap(
    *,
    result: DiagnosisResultPayload,
    uncertainty_notes: list[str],
) -> list[ConsultantDiagnosisRoadmapItem]:
    immediate_actions = _dedupe(
        [*result.next_actions, *[item.description for item in result.action_plan or []]],
        limit=4,
    )
    if not immediate_actions:
        immediate_actions = ["?꾩옱 媛쒖슂?먯꽌 洹쇨굅媛 ?쏀븳 臾몄옣 3媛쒕? ?좏깮??異쒖쿂 ?쇱씤??紐낆떆?⑸땲??"]

    mid_actions = _dedupe(
        [f"蹂댁셿 怨쇱젣: {gap.title} - {gap.description}" for gap in result.detailed_gaps or []],
        limit=4,
    )
    if not mid_actions:
        mid_actions = _dedupe(result.gaps, limit=3)
    if not mid_actions:
        mid_actions = ["?먭뎄 ?곗냽?깆쓣 蹂댁뿬以??꾩냽 ?쒕룞 怨꾪쉷???묒꽦?섍퀬 湲곕줉?⑸땲??"]

    long_actions = _dedupe(
        [f"二쇱젣 ?뺤옣: {topic}" for topic in result.recommended_topics or []],
        limit=4,
    )
    if not long_actions:
        long_actions = ["紐⑺몴 ?꾧났 ?곌퀎?깆씠 ?믪? 1媛?二쇱젣瑜??좎젙???ы솕 蹂닿퀬??珥덉븞???꾩꽦?⑸땲??"]

    return [
        ConsultantDiagnosisRoadmapItem(
            horizon="1_month",
            title="1媛쒖썡: 洹쇨굅 ?뺥빀???뺣━",
            actions=immediate_actions,
            success_signals=[
                "?듭떖 二쇱옣-洹쇨굅 留ㅽ븨???꾩꽦",
                "洹쇨굅 誘명솗??臾몄옣??'異붽? ?뺤씤 ?꾩슂' 紐낆떆",
            ],
            caution_notes=uncertainty_notes[:2],
        ),
        ConsultantDiagnosisRoadmapItem(
            horizon="3_months",
            title="3媛쒖썡: 蹂댁셿 異?吏묒쨷 媛쒖꽑",
            actions=mid_actions,
            success_signals=[
                "?쎌젏 異??곗냽??洹쇨굅諛??怨쇱젙?ㅻ챸) 理쒖냼 1媛??댁긽 媛쒖꽑 ?뺤씤",
                "?뺣웾 ?먮뒗 愿李?洹쇨굅媛 ?ы븿???щ? 異붽?",
            ],
            caution_notes=["?쒕룞 ?ъ떎??怨쇱옣?섏? 留먭퀬 ?ㅼ젣 ?섑뻾 踰붿쐞留?湲곕줉"],
        ),
        ConsultantDiagnosisRoadmapItem(
            horizon="6_months",
            title="6媛쒖썡: ?꾧났 ?곹빀???ㅽ넗由??꾩꽦",
            actions=long_actions,
            success_signals=[
                "?꾧났-援먭낵-?쒕룞 ?곌껐 臾몄옣???먯뿰?ㅻ읇寃??댁뼱吏?,
                "理쒖쥌 蹂닿퀬??珥덉븞?먯꽌 unsupported claim 鍮꾩쑉 媛먯냼",
            ],
            caution_notes=["?⑷꺽 媛?μ꽦 ?⑥젙 臾멸뎄 湲덉?", "寃利?遺덇? ?깆랬??蹂대쪟"],
        ),
    ]


async def _generate_narratives(
    *,
    project: Project,
    result: DiagnosisResultPayload,
    document_structure: dict[str, Any],
    uncertainty_notes: list[str],
) -> _NarrativeGenerationResult:
    fallback_summary = _build_fallback_executive_summary(result=result)
    fallback_memo = _build_fallback_final_memo(result=result)
    settings = get_settings()
    requested_provider = (settings.llm_provider or "gemini").strip().lower()
    requested_model = (
        (settings.ollama_render_model or settings.ollama_model or "gemma4").strip()
        if requested_provider == "ollama"
        else "gemini-1.5-pro"
    )
    fallback_execution = {
        "requested_llm_provider": requested_provider,
        "requested_llm_model": requested_model,
        "actual_llm_provider": "deterministic_fallback",
        "actual_llm_model": "deterministic_fallback",
        "llm_profile_used": "render",
        "fallback_used": True,
        "fallback_reason": "llm_unavailable",
    }

    context_payload = {
        "project_title": project.title,
        "target_university": project.target_university,
        "target_major": project.target_major,
        "headline": result.headline,
        "recommended_focus": result.recommended_focus,
        "strengths": result.strengths[:5],
        "gaps": result.gaps[:5],
        "next_actions": result.next_actions[:5],
        "recommended_topics": result.recommended_topics[:4],
        "weak_sections": document_structure.get("weak_sections", [])[:6],
        "uncertainty_notes": uncertainty_notes[:4],
        "required_section_order": list(_PREMIUM_SECTION_ORDER),
        "narrative_contract": {
            "executive_summary": "4-6臾몄옣, 洹쇨굅? 遺덊솗?ㅼ꽦 寃쎄퀎 ?ы븿",
            "current_record_status_brief": "?꾩옱 ?곹깭瑜?1-2臾몄옣?쇰줈 ?붿빟",
            "strengths_brief": "寃利앸맂 媛뺤젏 異??붿빟 1-2臾몄옣",
            "weaknesses_risks_brief": "蹂댁셿/由ъ뒪??異??붿빟 1-2臾몄옣",
            "major_fit_brief": "?꾧났 ?곹빀??異??붿빟 1-2臾몄옣",
            "section_diagnosis_brief": "?뱀뀡蹂?吏꾨떒 ?댁꽍 ?붿빟 1-2臾몄옣",
            "topic_strategy_brief": "二쇱젣쨌?꾨왂 ?붿빟 1-2臾몄옣",
            "roadmap_bridge": "1m/3m/6m ?곌껐 臾몄옣 1媛?,
            "uncertainty_bridge": "遺덊솗?ㅼ꽦 寃쎄퀎 臾몄옣 1媛?,
            "final_consultant_memo": "理쒖쥌 ?ㅽ뻾 肄붾찘??3-4臾몄옣",
        },
    }

    try:
        registry = get_prompt_registry()
        system_instruction = registry.compose_prompt("diagnosis.consultant-report-orchestration")
        prompt = (
            f"{registry.compose_prompt('diagnosis.executive-summary-writer')}\n\n"
            f"{registry.compose_prompt('diagnosis.roadmap-generator')}\n\n"
            "[吏꾨떒 而⑦뀓?ㅽ듃 JSON]\n"
            f"{json.dumps(context_payload, ensure_ascii=False, indent=2)}"
        )
    except (PromptAssetNotFoundError, PromptRegistryError) as exc:
        logger.warning(
            "Prompt registry unavailable for consultant narratives. Deterministic fallback applied: %s",
            exc,
        )
        fallback_execution["fallback_reason"] = "prompt_registry_unavailable"
        return _NarrativeGenerationResult(
            narrative=_ConsultantNarrativePayload(
                executive_summary=fallback_summary,
                current_record_status_brief=None,
                strengths_brief=None,
                weaknesses_risks_brief=None,
                major_fit_brief=None,
                section_diagnosis_brief=None,
                topic_strategy_brief=None,
                roadmap_bridge=None,
                uncertainty_bridge=None,
                final_consultant_memo=fallback_memo,
            ),
            execution_metadata=fallback_execution,
        )

    try:
        llm = get_llm_client(profile="render")
        response = await llm.generate_json(
            prompt=prompt,
            response_model=_ConsultantNarrativePayload,
            system_instruction=system_instruction,
            temperature=get_llm_temperature(profile="render"),
        )
        actual_provider = "ollama" if isinstance(llm, OllamaClient) else "gemini" if isinstance(llm, GeminiClient) else requested_provider
        actual_model = (
            llm.model
            if isinstance(llm, OllamaClient)
            else llm.model_name
            if isinstance(llm, GeminiClient)
            else requested_model
        )
        provider_fallback_used = actual_provider != requested_provider or actual_model != requested_model
        fallback_reason = "provider_auto_fallback" if provider_fallback_used else None
        return _NarrativeGenerationResult(
            narrative=_ConsultantNarrativePayload(
                executive_summary=response.executive_summary.strip() or fallback_summary,
                current_record_status_brief=(response.current_record_status_brief or "").strip() or None,
                strengths_brief=(response.strengths_brief or "").strip() or None,
                weaknesses_risks_brief=(response.weaknesses_risks_brief or "").strip() or None,
                major_fit_brief=(response.major_fit_brief or "").strip() or None,
                section_diagnosis_brief=(response.section_diagnosis_brief or "").strip() or None,
                topic_strategy_brief=(response.topic_strategy_brief or "").strip() or None,
                roadmap_bridge=(response.roadmap_bridge or "").strip() or None,
                uncertainty_bridge=(response.uncertainty_bridge or "").strip() or None,
                final_consultant_memo=response.final_consultant_memo.strip() or fallback_memo,
            ),
            execution_metadata={
                "requested_llm_provider": requested_provider,
                "requested_llm_model": requested_model,
                "actual_llm_provider": actual_provider,
                "actual_llm_model": actual_model,
                "llm_profile_used": "render",
                "fallback_used": provider_fallback_used,
                "fallback_reason": fallback_reason,
            },
        )
    except (LLMRequestError, RuntimeError, ValueError) as exc:
        logger.warning("Consultant narrative fallback applied: %s", exc)
        fallback_execution["fallback_reason"] = getattr(exc, "limited_reason", None) or sanitize_public_error(
            str(exc),
            fallback="llm_unavailable",
            max_length=120,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unexpected consultant narrative error. Fallback applied: %s", exc)
        fallback_execution["fallback_reason"] = sanitize_public_error(
            str(exc),
            fallback="llm_unavailable",
            max_length=120,
        )

    return _NarrativeGenerationResult(
        narrative=_ConsultantNarrativePayload(
            executive_summary=fallback_summary,
            current_record_status_brief=None,
            strengths_brief=None,
            weaknesses_risks_brief=None,
            major_fit_brief=None,
            section_diagnosis_brief=None,
            topic_strategy_brief=None,
            roadmap_bridge=None,
            uncertainty_bridge=None,
            final_consultant_memo=fallback_memo,
        ),
        execution_metadata=fallback_execution,
    )


def _enforce_narrative_contract(
    narrative: _ConsultantNarrativePayload,
    *,
    result: DiagnosisResultPayload,
    document_structure: dict[str, Any],
    uncertainty_notes: list[str],
) -> _ConsultantNarrativePayload:
    weak_sections = [str(item).strip() for item in document_structure.get("weak_sections", []) if str(item).strip()]
    verified_strength = (result.strengths or ["寃利?媛?ν븳 媛뺤젏 ?좏샇媛 ?쒗븳?곸엯?덈떎."])[0]
    primary_gap = (result.gaps or ["洹쇨굅 諛?꾩? 怨쇱젙 ?ㅻ챸 蹂닿컯???꾩슂?⑸땲??"])[0]
    major_fit_seed = (document_structure.get("subject_major_alignment_signals") or ["?꾧났 ?곌퀎 洹쇨굅 臾몄옣???쒗븳?곸엯?덈떎."])[0]
    section_density = document_structure.get("section_density") if isinstance(document_structure.get("section_density"), dict) else {}
    density_focus = ", ".join(f"{k}:{int(float(v) * 100)}%" for k, v in list(section_density.items())[:3]) if section_density else "?뱀뀡 諛???뺣낫媛 ?쒗븳?곸엯?덈떎."

    executive_summary = _guardrail_text(
        narrative.executive_summary,
        fallback=(
            f"?꾩옱 吏꾨떒 湲곗??먯꽌 ?뺤씤???듭떖 媛뺤젏? '{verified_strength}'?낅땲?? "
            f"?곗꽑 蹂댁셿異뺤? '{primary_gap}'?대ŉ, 臾몄옣-洹쇨굅 ?뺥빀??媛쒖꽑???꾩슂?⑸땲?? "
            "寃利앹씠 ?쏀븳 ??ぉ? '異붽? ?뺤씤 ?꾩슂'濡?遺꾨━??怨쇱옣 ?꾪뿕??李⑤떒?덉뒿?덈떎."
        ),
        max_len=1200,
    )
    if "異붽? ?뺤씤 ?꾩슂" not in executive_summary:
        executive_summary = f"{executive_summary} 洹쇨굅媛 ?쏀븳 ??ぉ? 異붽? ?뺤씤 ?꾩슂濡??쒓린?⑸땲??"

    final_memo = _guardrail_text(
        narrative.final_consultant_memo,
        fallback=_build_fallback_final_memo(result=result),
        max_len=1100,
    )

    return _ConsultantNarrativePayload(
        executive_summary=executive_summary,
        current_record_status_brief=_guardrail_text(
            narrative.current_record_status_brief,
            fallback=f"?꾩옱 湲곕줉 ?곹깭??'{result.recommended_focus or '洹쇨굅 以묒떖 蹂닿컯'}' 異뺤쓣 ?곗꽑 ?뺣젹?댁빞 ?⑸땲??",
            max_len=360,
        ),
        strengths_brief=_guardrail_text(
            narrative.strengths_brief,
            fallback=f"?뺤씤??媛뺤젏? '{verified_strength}'?대ŉ 洹쇨굅 ?곌껐?깆쓣 ?좎??댁빞 ?⑸땲??",
            max_len=360,
        ),
        weaknesses_risks_brief=_guardrail_text(
            narrative.weaknesses_risks_brief,
            fallback=f"?듭떖 由ъ뒪?щ뒗 '{primary_gap}'?닿퀬 ?쏀븳 ?뱀뀡? {', '.join(weak_sections[:3]) or '異붽? ?뺤씤 ?꾩슂 ??ぉ'}?낅땲??",
            max_len=360,
        ),
        major_fit_brief=_guardrail_text(
            narrative.major_fit_brief,
            fallback=f"?꾧났 ?곹빀???댁꽍? '{major_fit_seed}' 洹쇨굅瑜?湲곗??쇰줈 蹂댁닔?곸쑝濡??쒖떆?⑸땲??",
            max_len=360,
        ),
        section_diagnosis_brief=_guardrail_text(
            narrative.section_diagnosis_brief,
            fallback=f"?뱀뀡 諛??湲곗? ?듭떖 ?먭? 異뺤? {density_focus} ?낅땲??",
            max_len=360,
        ),
        topic_strategy_brief=_guardrail_text(
            narrative.topic_strategy_brief,
            fallback=f"二쇱젣 ?꾨왂? '{(result.recommended_topics or ['?꾧났 ?곌퀎 ?ы솕 二쇱젣'])[0]}' 以묒떖?쇰줈 ?④퀎???뺤옣??沅뚯옣?⑸땲??",
            max_len=360,
        ),
        roadmap_bridge=_guardrail_text(
            narrative.roadmap_bridge,
            fallback="濡쒕뱶留듭? 1媛쒖썡 ?뺥빀???뺣━, 3媛쒖썡 蹂댁셿異?媛쒖꽑, 6媛쒖썡 ?꾧났 ?ㅽ넗由??꾩꽦 ?쒖쑝濡??댁쁺?⑸땲??",
            max_len=360,
        ),
        uncertainty_bridge=_guardrail_text(
            narrative.uncertainty_bridge,
            fallback=f"遺덊솗?ㅼ꽦 寃쎄퀎: {(uncertainty_notes or ['寃利?遺議???ぉ? 異붽? ?뺤씤 ?꾩슂濡??좎?']) [0]}",
            max_len=360,
        ),
        final_consultant_memo=final_memo,
    )


def _guardrail_text(value: str | None, *, fallback: str, max_len: int) -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    text = re.sub(r"\s+", " ", text).strip()
    for forbidden in ("?⑷꺽 蹂댁옣", "臾댁“嫄??⑷꺽", "?뺤젙 ?⑷꺽", "諛섎뱶???⑷꺽", "????섑뻾"):
        text = text.replace(forbidden, "寃利??꾩슂")
    if len(text) > max_len:
        text = f"{text[: max_len - 1].rstrip()}??
    return text


def _enforce_section_architecture(
    sections: list[ConsultantDiagnosisSection],
    *,
    report_mode: DiagnosisReportMode,
) -> list[ConsultantDiagnosisSection]:
    expected = _PREMIUM_SECTION_ORDER if report_mode == "premium_10p" else _COMPACT_SECTION_ORDER
    section_map = {section.id: section for section in sections}
    ordered: list[ConsultantDiagnosisSection] = []
    for section_id in expected:
        existing = section_map.get(section_id)
        if existing is not None:
            ordered.append(existing)
            continue
        ordered.append(
            ConsultantDiagnosisSection(
                id=section_id,
                title=_humanize_section_title(section_id),
                subtitle="?먮룞 蹂댁셿 ?뱀뀡",
                body_markdown="- 援ъ“ ?쇨??깆쓣 ?꾪빐 湲곕낯 ?뱀뀡 ????좎??덉뒿?덈떎.\n- 洹쇨굅媛 遺議깊븳 ??ぉ? 異붽? ?뺤씤 ?꾩슂濡?愿由ы빀?덈떎.",
            )
        )
    return ordered


def _humanize_section_title(section_id: str) -> str:
    title_map = {
        "executive_summary": "Executive Summary",
        "record_baseline_dashboard": "Academic & Record Baseline Dashboard",
        "narrative_timeline": "Narrative Timeline",
        "evidence_cards": "Evidence Cards",
        "strength_analysis": "Strength Analysis",
        "risk_analysis": "Risk Analysis",
        "major_fit": "Target-Major Fit Interpretation",
        "interview_questions": "Probable Interview Questions",
        "roadmap": "Action Roadmap",
    }
    return title_map.get(section_id, section_id)


def _build_fallback_executive_summary(*, result: DiagnosisResultPayload) -> str:
    strength = result.strengths[0] if result.strengths else "?꾩옱 湲곕줉?먮뒗 ?쒖슜 媛?ν븳 湲곕낯 媛뺤젏???뺤씤?⑸땲??"
    gap = result.gaps[0] if result.gaps else "?ㅼ쓬 ?④퀎?먯꽌??洹쇨굅 諛?꾩? 怨쇱젙 ?ㅻ챸???곗꽑 蹂댁셿?댁빞 ?⑸땲??"
    return (
        f"蹂?吏꾨떒? '{result.headline}'瑜?以묒떖?쇰줈 ?숈깮遺 洹쇨굅瑜??ш??좏뻽?듬땲?? "
        f"?뺤씤??媛뺤젏? '{strength}'?대ŉ, ?듭떖 蹂댁셿異뺤? '{gap}'?낅땲?? "
        "?꾩옱 ?곹깭?먯꽌 媛??以묒슂???꾨왂? 寃利?媛?ν븳 ?щ?瑜?以묒떖?쇰줈 媛쒖슂瑜??ъ젙?ы븯怨? "
        "洹쇨굅媛 ?쏀븳 臾몄옣??'異붽? ?뺤씤 ?꾩슂'濡?紐낆떆??怨쇱옣 媛?μ꽦??李⑤떒?섎뒗 寃껋엯?덈떎."
    )


def _build_fallback_final_memo(*, result: DiagnosisResultPayload) -> str:
    focus = result.recommended_focus or "洹쇨굅 ?곌껐 媛뺥솕"
    next_step = result.next_actions[0] if result.next_actions else "媛쒖슂???ㅼ쓬 ?뚮떒??1媛쒕? 洹쇨굅 以묒떖?쇰줈 ?ъ옉??
    return (
        "理쒖쥌 肄붾찘?? ?꾩옱 ?먮즺留뚯쑝濡쒕룄 諛⑺뼢?깆? 異⑸텇???꾩텧?⑸땲?? "
        f"?ㅻ쭔 '{focus}'瑜??곗꽑 怨쇱젣濡??먭퀬, '{next_step}'瑜??ㅽ뻾??臾몄옣-洹쇨굅 ?뺥빀?깆쓣 癒쇱? ?뚯뼱?щ━??寃껋씠 ?덉쟾?⑸땲?? "
        "?⑷꺽 ?덉륫??臾멸뎄??寃利앸릺吏 ?딆? ?깆랬 ?쒖닠? 諛곗젣?섍퀬, 洹쇨굅媛 ?뺣낫??臾몄옣遺???꾩꽦?꾨? ?믪씠??떆??"
    )


def _build_sections(
    *,
    result: DiagnosisResultPayload,
    report_mode: DiagnosisReportMode,
    target_context: str,
    evidence_items: list[ConsultantDiagnosisEvidenceItem],
    score_groups: list[ConsultantDiagnosisScoreGroup],
    document_structure: dict[str, Any],
    evidence_bank: list[dict[str, Any]],
    roadmap: list[ConsultantDiagnosisRoadmapItem],
    narratives: _ConsultantNarrativePayload,
    uncertainty_notes: list[str],
    reanalysis_required: bool,
) -> list[ConsultantDiagnosisSection]:
    top_citations = _build_diverse_evidence_items(
        evidence_items=evidence_items,
        evidence_bank=evidence_bank,
        limit=24,
    )
    if not top_citations:
        top_citations = evidence_items[:10]
    evidence_cursor = 0

    def pick_evidence(count: int) -> list[ConsultantDiagnosisEvidenceItem]:
        nonlocal evidence_cursor
        if count <= 0 or not top_citations:
            return []
        window_size = min(count, len(top_citations))
        selected = [
            top_citations[(evidence_cursor + offset) % len(top_citations)]
            for offset in range(window_size)
        ]
        evidence_cursor = (evidence_cursor + count) % len(top_citations)
        return selected

    weak_sections = [str(item).strip() for item in document_structure.get("weak_sections", []) if str(item).strip()]
    timeline_signals = [str(item).strip() for item in document_structure.get("timeline_signals", []) if str(item).strip()]
    alignment_signals = [str(item).strip() for item in document_structure.get("subject_major_alignment_signals", []) if str(item).strip()]
    continuity_signals = [str(item).strip() for item in document_structure.get("continuity_signals", []) if str(item).strip()]
    process_signals = [str(item).strip() for item in document_structure.get("process_reflection_signals", []) if str(item).strip()]
    coverage_check = (
        document_structure.get("coverage_check")
        if isinstance(document_structure.get("coverage_check"), dict)
        else {}
    )
    section_density = (
        document_structure.get("section_density")
        if isinstance(document_structure.get("section_density"), dict)
        else {}
    )

    student_score_group = next((group for group in score_groups if group.group == "student_evaluation"), None)
    system_score_group = next((group for group in score_groups if group.group == "system_quality"), None)
    score_lines: list[str] = []
    for group in (student_score_group, system_score_group):
        if not group:
            continue
        score_lines.append(f"[{group.title}]")
        for block in group.blocks:
            score_lines.append(f"{block.label}: {block.score}??({block.band})")

    evidence_cards = evidence_bank[:6]
    evidence_card_lines: list[str] = []
    for idx, card in enumerate(evidence_cards, start=1):
        quote = _clean_line(str(card.get("quote") or ""), max_len=62)
        interpretation = _clean_line(str(card.get("theme") or "?듭떖 ?쒕룞"), max_len=28)
        why_it_matters = _clean_line(
            ", ".join(str(item) for item in (card.get("major_relevance") or [])[:2]) or "?꾧났 ?곌퀎",
            max_len=26,
        )
        risk_note = "?ㅻ챸 ?뺤옣 ?꾩슂" if not bool((card.get("process_elements") or {}).get("limitation")) else "?쒓퀎 ?몄떇 ?ы븿"
        evidence_card_lines.append(
            f"[移대뱶 {idx}] p.{card.get('page')} | ?먮Ц: {quote} | ?댁꽍: {interpretation} | ?섎?: {why_it_matters} | 由ъ뒪?? {risk_note}"
        )

    interview_questions = _dedupe(
        [
            "吏?띻???嫄댁텞??愿?ъ쓣 媛뽮쾶 ??援ъ껜??怨꾧린??臾댁뾿?멸???",
            "?щ궃쨌湲고썑 ???愿?먯뿉??蹂몄씤???먭뎄瑜???臾몄옣?쇰줈 ?ㅻ챸??蹂댁꽭??",
            "援ъ“/?щ즺 ?좏깮?먯꽌 ?대뼡 湲곗??쇰줈 ?먮떒?덈뒗吏 ?ㅻ챸??蹂댁꽭??",
            "?ъ슜??寃쏀뿕?대굹 怨듦컙 ?몃Ц 愿?먯뿉??蹂댁셿?섍퀬 ?띠? ?먯? 臾댁뾿?멸???",
            "援먭낵 ?명듅???먭뎄瑜??ㅼ젣 ?ㅺ퀎 ?ш퀬濡??곌껐???щ?媛 ?덈굹??",
            "?ν썑 6媛쒖썡 ?숈븞 ?ㅽ넗由щ씪?몄쓣 媛뺥솕?섍린 ?꾪븳 ?ㅽ뻾 怨꾪쉷? 臾댁뾿?멸???",
            *[f"洹쇨굅 湲곕컲 ?뺤씤 吏덈Ц: {signal}" for signal in continuity_signals[:2]],
        ],
        limit=8,
    )

    roadmap_lines: list[str] = []
    for item in roadmap:
        roadmap_lines.append(item.title)
        roadmap_lines.extend([f"- {action}" for action in item.actions[:3]])

    storyline = "?щ궃/湲고썑 ??묓삎 吏?띻???嫄댁텞"
    one_line_verdict = (
        "?꾧났 ?곹빀?깆? ?믨퀬 ?곗냽?깅룄 ?뺤씤?섏?留? ?쒖궗 異뺤씠 遺꾩궛?섏뼱 ?덉뼱 "
        f"'{storyline}' ??以꾨줈 ?듯빀???꾩슂?⑸땲??"
    )
    if reanalysis_required:
        one_line_verdict = (
            "?щ텇???꾩슂: ?꾩닔 ?뱀뀡 異붿텧 而ㅻ쾭由ъ?媛 遺議깊븯???숈깮 ?됯? ?먯닔??李멸퀬?⑹쑝濡쒕쭔 ?쒖떆?⑸땲??"
        )

    baseline_lines = [
        target_context,
        f"遺꾩꽍 ?좊ː?? {int(round(float(coverage_check.get('coverage_score', 0.0)) * 100))}%",
        *(score_lines[:14] or ["?먯닔 ?곗씠?곌? ?쒗븳?곸엯?덈떎."]),
        f"?뱀뀡 而ㅻ쾭由ъ? ?꾨씫: {', '.join(coverage_check.get('missing_required_sections', [])[:5]) or '?놁쓬'}",
    ]

    timeline_lines = timeline_signals[:6] or ["?숇뀈蹂??곗냽 ?좏샇媛 ?쒗븳?곸씠?댁꽌 ?섏씠吏 洹쇨굅 以묒떖?쇰줈 ?ъ젙?ъ씠 ?꾩슂?⑸땲??"]
    fit_lines = [
        narratives.major_fit_brief or "嫄댁텞 愿???곗냽?깆? 媛뺥븯吏留? ?ㅽ넗由щ씪???듯빀???곗꽑 怨쇱젣?낅땲??",
        "媛뺤젏 異? 湲곗닠/援ъ“/?щ즺/?섍꼍 ?뚮쭏???꾩쟻",
        "蹂댁셿 異? ?붿옄???몄뼱쨌?ъ슜??寃쏀뿕쨌怨듦컙 ?몃Ц ?꾨젅?대컢",
        f"沅뚯옣 ?듯빀 ?쒖궗: {storyline}",
        *(alignment_signals[:2] or []),
    ]

    sections = [
        ConsultantDiagnosisSection(
            id="executive_summary",
            title="Executive Summary",
            subtitle="??以??먯젙 쨌 媛뺤젏 3 쨌 由ъ뒪??3",
            body_markdown=_bulleted(
                [
                    f"??以??먯젙: {one_line_verdict}",
                    *(result.strengths[:3] or ["?듭떖 媛뺤젏 洹쇨굅媛 ?쒗븳?곸엯?덈떎."]),
                    *(result.gaps[:3] or ["?듭떖 由ъ뒪??洹쇨굅媛 ?쒗븳?곸엯?덈떎."]),
                    f"理쒖슦???≪뀡: {result.recommended_focus}",
                ]
            ),
            evidence_items=pick_evidence(3),
            additional_verification_needed=uncertainty_notes[:2] if reanalysis_required else [],
        ),
        ConsultantDiagnosisSection(
            id="record_baseline_dashboard",
            title="Academic & Record Baseline Dashboard",
            subtitle="?숈깮 ?됯? ?먯닔? ?쒖뒪???덉쭏 ?먯닔 遺꾨━",
            body_markdown=_bulleted(baseline_lines),
            evidence_items=pick_evidence(2),
            additional_verification_needed=weak_sections[:3],
        ),
        ConsultantDiagnosisSection(
            id="narrative_timeline",
            title="Narrative Timeline",
            subtitle="?숇뀈蹂?愿??吏꾪솕 ?먮쫫",
            body_markdown=_bulleted(
                [
                    "1?숇뀈 ??湲곗큹 ?먯깋怨?二쇱젣 諛쒓껄",
                    "2?숇뀈 ??援ъ“/?щ즺/?섍꼍 ?뚮쭏 ?ы솕",
                    "3?숇뀈 ???꾧났 ?곌퀎 ?ㅽ넗由??듯빀 ?꾩슂",
                    *timeline_lines,
                ]
            ),
            evidence_items=pick_evidence(2),
        ),
        ConsultantDiagnosisSection(
            id="evidence_cards",
            title="Evidence Cards",
            subtitle="?듭떖 洹쇨굅 6媛?移대뱶",
            body_markdown=_bulleted(evidence_card_lines or ["?듭떖 洹쇨굅 移대뱶 ?앹꽦???꾩슂???듭빱媛 遺議깊빀?덈떎."]),
            evidence_items=pick_evidence(4),
            unsupported_claims=["?먮Ц???녿뒗 ?섏긽쨌?깆랬쨌?ㅽ뿕 寃곌낵???앹꽦?섏? ?딆뒿?덈떎."],
        ),
        ConsultantDiagnosisSection(
            id="strength_analysis",
            title="Strength Analysis",
            subtitle="?곸쐞 媛뺤젏 吏꾨떒",
            body_markdown=_bulleted(
                [
                    *(result.strengths[:3] or ["媛뺤젏 吏꾩닠???쒗븳?곸엯?덈떎."]),
                    narratives.strengths_brief or "媛뺤젏? ?섏씠吏 洹쇨굅? 吏곸젒 ?곌껐?섏뼱???⑸땲??",
                    *(process_signals[:2] or []),
                ]
            ),
            evidence_items=(
                [item for item in pick_evidence(4) if item.support_status == "verified"][:3]
                or pick_evidence(3)
            ),
        ),
        ConsultantDiagnosisSection(
            id="risk_analysis",
            title="Risk Analysis",
            subtitle="?곸쐞 由ъ뒪??吏꾨떒",
            body_markdown=_bulleted(
                [
                    *(result.gaps[:3] or ["由ъ뒪??吏꾩닠???쒗븳?곸엯?덈떎."]),
                    "?듭떖 由ъ뒪?щ뒗 ?꾧났 遺?곹빀???꾨땲???쒖궗 遺꾩궛?낅땲??",
                    *(weak_sections[:3] or ["?쏀븳 ?뱀뀡? ?щ텇?????뺤젙???꾩슂?⑸땲??"]),
                ]
            ),
            evidence_items=pick_evidence(3),
            additional_verification_needed=uncertainty_notes[:3],
            unsupported_claims=["寃利앸릺吏 ?딆? ?⑷꺽 ?덉륫/蹂댁옣 臾멸뎄 湲덉?"],
        ),
        ConsultantDiagnosisSection(
            id="major_fit",
            title="Target-Major Fit Interpretation",
            subtitle="?쒖슱? 嫄댁텞 吏留?湲곗? ?댁꽍",
            body_markdown=_bulleted(fit_lines),
            evidence_items=pick_evidence(3),
            additional_verification_needed=["?붿옄???몄뼱쨌?ъ슜??寃쏀뿕 愿??洹쇨굅 移대뱶 蹂닿컯"],
        ),
        ConsultantDiagnosisSection(
            id="interview_questions",
            title="Probable Interview Questions",
            subtitle="硫댁젒 ?덉긽 吏덈Ц",
            body_markdown=_bulleted(interview_questions),
            evidence_items=pick_evidence(2),
        ),
        ConsultantDiagnosisSection(
            id="roadmap",
            title="Action Roadmap",
            subtitle="1媛쒖썡 쨌 3媛쒖썡 쨌 6媛쒖썡 ?ㅽ뻾 怨꾪쉷",
            body_markdown=_bulleted(
                [
                    narratives.roadmap_bridge or "?④퀎蹂??ㅽ뻾 怨꾪쉷? 洹쇨굅 蹂닿컯怨??ㅽ넗由??듯빀 ?쒖쑝濡?吏꾪뻾?⑸땲??",
                    *roadmap_lines,
                ]
            ),
            evidence_items=pick_evidence(2),
        ),
    ]

    if report_mode == "compact":
        return sections[:5]
    return sections


def _build_diverse_evidence_items(
    *,
    evidence_items: list[ConsultantDiagnosisEvidenceItem],
    evidence_bank: list[dict[str, Any]],
    limit: int,
) -> list[ConsultantDiagnosisEvidenceItem]:
    candidates: list[ConsultantDiagnosisEvidenceItem] = [*evidence_items]
    for item in evidence_bank:
        quote = _clean_line(str(item.get("quote") or ""), max_len=230)
        if not quote:
            continue
        page_number = _coerce_positive_int(item.get("page"))
        anchor_id = str(item.get("anchor_id") or "").strip()
        section = str(item.get("section") or "").strip()
        confidence = _coerce_float(item.get("confidence"), default=0.7)
        support_status: str
        if confidence >= 0.8:
            support_status = "verified"
        elif confidence >= 0.55:
            support_status = "probable"
        else:
            support_status = "needs_verification"
        source_base = f"?숈깮遺 ?듭빱 {anchor_id}" if anchor_id else f"?숈깮遺 p.{page_number}" if page_number else "?숈깮遺 ?듭빱"
        source_label = f"{section} | {source_base}" if section else source_base
        candidates.append(
            ConsultantDiagnosisEvidenceItem(
                source_label=source_label,
                page_number=page_number,
                excerpt=quote,
                relevance_score=round(max(0.0, min(1.0, confidence)) * 2.0, 3),
                support_status=support_status,  # type: ignore[arg-type]
            )
        )

    deduped: list[ConsultantDiagnosisEvidenceItem] = []
    seen: set[tuple[str, int, str]] = set()
    for candidate in candidates:
        key = (
            str(candidate.source_label or "").strip(),
            int(candidate.page_number or 0),
            _clean_line(candidate.excerpt, max_len=90),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)

    diversified: list[ConsultantDiagnosisEvidenceItem] = []
    seen_pages: set[int] = set()
    remainder: list[ConsultantDiagnosisEvidenceItem] = []
    for candidate in deduped:
        page_number = int(candidate.page_number or 0)
        if page_number > 0 and page_number not in seen_pages:
            diversified.append(candidate)
            seen_pages.add(page_number)
        else:
            remainder.append(candidate)
        if len(diversified) >= limit:
            return diversified[:limit]

    for candidate in remainder:
        diversified.append(candidate)
        if len(diversified) >= limit:
            break
    return diversified[:limit]


def _build_appendix_notes(documents: list[Any], document_structure: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    for document in documents:
        metadata = getattr(document, "parse_metadata", None)
        if not isinstance(metadata, dict):
            continue
        warnings = metadata.get("warnings")
        if isinstance(warnings, list):
            for warning in warnings:
                text = str(warning).strip()
                if text:
                    notes.append(f"?뚯떛 寃쎄퀬: {text}")
        confidence = metadata.get("parse_confidence")
        if isinstance(confidence, (int, float)):
            notes.append(f"?뚯떛 confidence={round(float(confidence), 3)}")
        quality_score = metadata.get("pipeline_quality_score")
        if isinstance(quality_score, (int, float)):
            notes.append(f"?뚯씠?꾨씪??quality_score={round(float(quality_score), 3)}")
    for item in document_structure.get("uncertain_items", [])[:5]:
        notes.append(f"援ъ“ 異붿젙 遺덊솗????ぉ: {item}")
    return _dedupe(notes, limit=20)


def _build_failed_report_payload(
    *,
    run: DiagnosisRun,
    project: Project,
    report_mode: DiagnosisReportMode,
    template_id: str,
) -> str:
    payload = ConsultantDiagnosisReport(
        diagnosis_run_id=run.id,
        project_id=project.id,
        report_mode=report_mode,
        template_id=template_id,
        title=f"{project.title} ?꾨Ц 而⑥꽕?댄듃 吏꾨떒??,
        subtitle="?앹꽦 ?ㅽ뙣 - ?쒗븳 ?뺣낫",
        student_target_context=f"?꾨줈?앺듃: {project.title}",
        generated_at=datetime.now(timezone.utc),
        score_blocks=[],
        sections=[
            ConsultantDiagnosisSection(
                id="generation_failed",
                title="吏꾨떒???앹꽦 ?ㅽ뙣",
                subtitle=None,
                body_markdown="?붿껌??吏꾨떒?쒕? ?앹꽦?섏? 紐삵뻽?듬땲?? ?꾨줈?앺듃 洹쇨굅 臾몄꽌瑜??뺤씤?????ъ떆?꾪빐 二쇱꽭??",
            )
        ],
        roadmap=[],
        citations=[],
        uncertainty_notes=["由ы룷???앹꽦 ?ㅽ뙣濡??명빐 ?곸꽭 遺꾩꽍???ы븿?섏? ?딆븯?듬땲??"],
        final_consultant_memo="洹쇨굅 臾몄꽌 ?곹깭 ?뺤씤 ???ъ깮?깊빐 二쇱꽭??",
        appendix_notes=[],
        render_hints={"a4": True, "minimum_pages": 1},
    )
    return payload.model_dump_json()


def _clean_line(value: str | None, *, max_len: int) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 1].rstrip()}??


def _coerce_positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _coerce_float(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if parsed != parsed:  # NaN guard
        return default
    return parsed


def _bulleted(lines: list[str]) -> str:
    cleaned = [str(item).strip() for item in lines if str(item).strip()]
    return "\n".join(f"- {line}" for line in cleaned)


def _dedupe(items: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for raw in items:
        normalized = str(raw or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
        if len(deduped) >= limit:
            break
    return deduped


def _normalize_section_name(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    alias = {
        "grades_subjects": "援먭낵?숈뒿諛쒕떖?곹솴",
        "grades_and_notes": "援먭낵?숈뒿諛쒕떖?곹솴",
        "subject_special_notes": "?명듅",
        "creative_activities": "李쎌껜",
        "extracurricular": "李쎌껜",
        "volunteer": "李쎌껜",
        "career_signals": "吏꾨줈",
        "reading": "?낆꽌",
        "reading_activity": "?낆꽌",
        "behavior_general_comments": "?됰룞?뱀꽦",
        "behavior_opinion": "?됰룞?뱀꽦",
    }
    return alias.get(text, text)

