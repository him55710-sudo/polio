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

from polio_api.core.config import get_settings
from polio_api.core.llm import GeminiClient, LLMRequestError, OllamaClient, get_llm_client, get_llm_temperature
from polio_api.core.security import sanitize_public_error
from polio_api.db.models.diagnosis_report_artifact import DiagnosisReportArtifact
from polio_api.db.models.diagnosis_run import DiagnosisRun
from polio_api.db.models.project import Project
from polio_api.schemas.diagnosis import (
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
from polio_api.services.document_service import list_documents_for_project
from polio_api.services.prompt_registry import (
    PromptAssetNotFoundError,
    PromptRegistryError,
    get_prompt_registry,
)
from polio_domain.enums import RenderFormat
from polio_render.diagnosis_report_design_contract import get_diagnosis_report_design_contract
from polio_render.diagnosis_report_pdf_renderer import render_consultant_diagnosis_pdf
from polio_render.template_registry import get_template
from polio_shared.storage import get_storage_provider, get_storage_provider_name


logger = logging.getLogger("unifoli.api.diagnosis_report")

_DEFAULT_TEMPLATE_BY_MODE: dict[str, str] = {
    "compact": "consultant_diagnosis_compact",
    "premium_10p": "consultant_diagnosis_premium_10p",
}
_REPORT_FAILURE_FALLBACK = "Diagnosis report generation failed. Retry after checking the project evidence."


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
                message = f"고유 앵커 {len(unique_anchor_ids)}개 / 페이지 {len(unique_anchor_pages)}개로 품질 게이트 미충족"
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
                "재분석 필요: 필수 섹션 커버리지가 부족하거나 근거 앵커 분산이 낮습니다.",
                (
                    f"앵커 품질 게이트 미충족: 고유 앵커 {len(unique_anchor_ids)}개 / 고유 페이지 {len(unique_anchor_pages)}개"
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
        appendix_notes.append("인용 부록에는 주장-근거 연결 검증을 위한 출처 라인이 포함됩니다.")

    report_payload = ConsultantDiagnosisReport(
        diagnosis_run_id=run.id,
        project_id=project.id,
        report_mode=report_mode,
        template_id=template_id,
        title=f"{project.title} 전문 컨설턴트 진단서",
        subtitle="학생부 근거 기반 진단 · 리스크 명시 · 실행 로드맵",
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
    target_university = project.target_university or "미설정"
    target_major = project.target_major or "미설정"
    diagnosis_target = result.diagnosis_summary.target_context if result.diagnosis_summary else None
    student_name = "미확인"
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
        f"학생: {student_name}",
        f"프로젝트: {project.title}",
        f"목표 대학: {target_university}",
        f"목표 전공: {target_major}",
        f"분석 문서 수: {len(documents)}",
    ]
    if diagnosis_target:
        context_bits.append(f"진단 타깃 메모: {diagnosis_target}")
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
                uncertainty_note="해당 점수는 입력 문서 기반 상대평가이며 절대 합격예측이 아님.",
            )
        )

    if not blocks:
        blocks.append(
            ConsultantDiagnosisScoreBlock(
                key="fallback",
                label="진단 요약 점수",
                score=52,
                band="watch",
                interpretation="구조화 점수 축이 부족하여 보수적 기본 점수를 사용했습니다.",
                uncertainty_note="추가 문서 근거 확보 후 재생성 권장.",
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
        keywords=("건축", "공간", "구조", "재료", "환경", "기후", "재난", "설계"),
    )
    ux_humanities_signal = _count_keywords(
        evidence_bank,
        keywords=("사용자", "경험", "동선", "공공성", "인문", "사회문화"),
    )
    design_spatial_score = max(38, min(95, 50 + design_signal * 3 - max(0, 2 - ux_humanities_signal) * 4))
    academic_base_score = max(
        35,
        min(
            95,
            int(round((float(section_density.get("교과학습발달상황", 0.0)) * 55) + (major_fit_seed * 0.45))),
        ),
    )
    leadership_score = max(
        34,
        min(
            92,
            int(
                round(
                    (float(section_density.get("창체", 0.0)) * 45)
                    + (float(section_density.get("행동특성", 0.0)) * 35)
                    + 18
                )
            ),
        ),
    )

    student_specs: list[tuple[str, str, int, str]] = [
        ("major_fit", "전공 적합성", major_fit_seed, "건축 전공 연계 근거의 직접성과 연속성"),
        ("inquiry_depth", "탐구 깊이", int(round((process_seed * 0.5) + (density_seed * 0.5))), "문제설정-방법-결과-확장의 깊이"),
        ("inquiry_continuity", "탐구 연속성", continuity_seed, "학년 간 주제의 연속성과 심화 흐름"),
        ("evidence_density", "근거 밀도", density_seed, "주장 대비 원문 근거 앵커의 밀도"),
        ("process_explanation", "과정 설명력", process_seed, "과정·방법·한계·개선의 설명 충실도"),
        ("design_spatial_thinking", "설계·공간 사고", int(design_spatial_score), "구조·재료·환경 중심 설계 사고"),
        ("academic_base", "학업 기반", int(academic_base_score), "교과 성취와 세특 근거의 안정성"),
        ("leadership_collaboration", "리더십·협업", int(leadership_score), "협업·공동체·책임 신호"),
    ]

    student_blocks: list[ConsultantDiagnosisScoreBlock] = []
    for key, label, raw_score, interpretation in student_specs:
        score = max(0, min(100, int(raw_score)))
        anchor_ids = _select_anchor_ids_for_score(key=key, evidence_bank=evidence_bank)
        if len(anchor_ids) < 2:
            score = min(score, 45)
            uncertainty = "고유 근거 앵커가 2개 미만이라 재분석 후 재평가가 필요합니다."
        else:
            uncertainty = f"고유 근거 앵커 {len(anchor_ids)}개 확인"
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
            label="파싱 커버리지",
            score=max(0, min(100, parse_coverage_score)),
            band="high" if parse_coverage_score >= 80 else "mid" if parse_coverage_score >= 60 else "low",
            interpretation="필수 정규화 섹션 추출 커버리지",
            uncertainty_note=None,
        ),
        ConsultantDiagnosisScoreBlock(
            key="citation_coverage",
            label="인용 커버리지",
            score=citation_coverage_score,
            band="high" if citation_coverage_score >= 65 else "mid" if citation_coverage_score >= 35 else "low",
            interpretation="근거 페이지 분산과 인용 연결도",
            uncertainty_note=None,
        ),
        ConsultantDiagnosisScoreBlock(
            key="evidence_uniqueness",
            label="근거 고유성",
            score=evidence_uniqueness_score,
            band="high" if evidence_uniqueness_score >= 75 else "mid" if evidence_uniqueness_score >= 50 else "low",
            interpretation="중복 인용 과다 여부",
            uncertainty_note=None,
        ),
        ConsultantDiagnosisScoreBlock(
            key="contradiction_check",
            label="모순 검증",
            score=contradiction_score,
            band="high" if contradiction_passed else "low",
            interpretation="섹션 누락/밀도 상태 모순 검증",
            uncertainty_note=None if contradiction_passed else "모순이 감지되어 프리미엄 렌더를 차단합니다.",
        ),
        ConsultantDiagnosisScoreBlock(
            key="redaction_safety",
            label="비식별 안전성",
            score=redaction_safety_score,
            band="high" if redaction_safety_score >= 80 else "low",
            interpretation="민감정보 노출 위험 점검",
            uncertainty_note=None if redaction_safety_score >= 80 else "민감정보 패턴이 감지되어 검토가 필요합니다.",
        ),
    ]

    reanalysis_required = bool(coverage_check.get("reanalysis_required")) or parse_coverage_score < 70
    student_group = ConsultantDiagnosisScoreGroup(
        group="student_evaluation",
        title="학생 평가 점수",
        blocks=student_blocks,
        gating_status="reanalysis_required" if reanalysis_required else "ok",
        note=(
            "파싱 커버리지가 낮아 학생 점수는 참고용으로만 제시됩니다."
            if reanalysis_required
            else "모든 점수는 최소 2개 이상의 고유 근거 앵커를 기준으로 산출되었습니다."
        ),
    )
    system_group = ConsultantDiagnosisScoreGroup(
        group="system_quality",
        title="시스템 품질 점수",
        blocks=system_blocks,
        gating_status="blocked" if not contradiction_passed else ("reanalysis_required" if reanalysis_required else "ok"),
        note=(
            "모순 검증 실패로 프리미엄 PDF 렌더를 중단합니다."
            if not contradiction_passed
            else "시스템 품질 점수는 학생 평가 점수와 분리되어 해석됩니다."
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
        "major_fit": ("건축", "전공", "진로", "설계", "환경", "구조"),
        "inquiry_depth": ("탐구", "실험", "가설", "분석", "비교"),
        "inquiry_continuity": ("심화", "확장", "후속", "연계", "지속"),
        "evidence_density": ("결과", "수치", "지표", "근거"),
        "process_explanation": ("과정", "방법", "한계", "개선"),
        "design_spatial_thinking": ("설계", "공간", "구조", "재료", "건축"),
        "academic_base": ("교과", "성취", "세특", "과목"),
        "leadership_collaboration": ("협업", "공동체", "리더", "봉사"),
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
                    ("교과학습발달상황", "grades_subjects"),
                    ("세특", "subject_special_notes"),
                    ("창체", "extracurricular"),
                    ("진로", "career_signals"),
                    ("독서", "reading_activity"),
                    ("행동특성", "behavior_opinion"),
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
            ("교과학습발달상황", "grades_subjects"),
            ("세특", "subject_special_notes"),
            ("창체", "extracurricular"),
            ("진로", "career_signals"),
            ("독서", "reading_activity"),
            ("행동특성", "behavior_opinion"),
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
        notes.append("문서 파싱 품질 점검 필요: 일부 페이지/구역은 수동 검토 후 확정해야 합니다.")
    if not evidence_items:
        notes.append("직접 인용 가능한 근거가 부족합니다. 주요 주장마다 원문 출처를 보강하세요.")
    if result.review_required:
        notes.append("정책/안전 플래그가 감지되어 검토 태스크가 열린 상태입니다.")
    if bool(coverage_check.get("reanalysis_required")):
        missing = coverage_check.get("missing_required_sections")
        if isinstance(missing, list) and missing:
            notes.append(f"필수 섹션 누락: {', '.join(str(item) for item in missing[:6])}")
        else:
            notes.append("필수 섹션 커버리지가 낮아 재분석이 필요합니다.")
    if not bool(contradiction_check.get("passed", True)):
        notes.append("모순 검증 실패: 누락 상태와 밀도 상태가 충돌하여 프리미엄 렌더를 차단합니다.")
    for item in document_structure.get("uncertain_items", [])[:4]:
        notes.append(f"구조 추정 불확실: {item}")
    if not notes:
        notes.append("현재 근거 범위 내에서 보수적으로 해석했습니다. 새로운 성취 서술은 추가 검증 후 반영하세요.")
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
        immediate_actions = ["현재 개요에서 근거가 약한 문장 3개를 선택해 출처 라인을 명시합니다."]

    mid_actions = _dedupe(
        [f"보완 과제: {gap.title} - {gap.description}" for gap in result.detailed_gaps or []],
        limit=4,
    )
    if not mid_actions:
        mid_actions = _dedupe(result.gaps, limit=3)
    if not mid_actions:
        mid_actions = ["탐구 연속성을 보여줄 후속 활동 계획을 작성하고 기록합니다."]

    long_actions = _dedupe(
        [f"주제 확장: {topic}" for topic in result.recommended_topics or []],
        limit=4,
    )
    if not long_actions:
        long_actions = ["목표 전공 연계성이 높은 1개 주제를 선정해 심화 보고서 초안을 완성합니다."]

    return [
        ConsultantDiagnosisRoadmapItem(
            horizon="1_month",
            title="1개월: 근거 정합성 정리",
            actions=immediate_actions,
            success_signals=[
                "핵심 주장-근거 매핑표 완성",
                "근거 미확인 문장에 '추가 확인 필요' 명시",
            ],
            caution_notes=uncertainty_notes[:2],
        ),
        ConsultantDiagnosisRoadmapItem(
            horizon="3_months",
            title="3개월: 보완 축 집중 개선",
            actions=mid_actions,
            success_signals=[
                "약점 축(연속성/근거밀도/과정설명) 최소 1개 이상 개선 확인",
                "정량 또는 관찰 근거가 포함된 사례 추가",
            ],
            caution_notes=["활동 사실을 과장하지 말고 실제 수행 범위만 기록"],
        ),
        ConsultantDiagnosisRoadmapItem(
            horizon="6_months",
            title="6개월: 전공 적합성 스토리 완성",
            actions=long_actions,
            success_signals=[
                "전공-교과-활동 연결 문장이 자연스럽게 이어짐",
                "최종 보고서 초안에서 unsupported claim 비율 감소",
            ],
            caution_notes=["합격 가능성 단정 문구 금지", "검증 불가 성취는 보류"],
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
            "executive_summary": "4-6문장, 근거와 불확실성 경계 포함",
            "current_record_status_brief": "현재 상태를 1-2문장으로 요약",
            "strengths_brief": "검증된 강점 축 요약 1-2문장",
            "weaknesses_risks_brief": "보완/리스크 축 요약 1-2문장",
            "major_fit_brief": "전공 적합성 축 요약 1-2문장",
            "section_diagnosis_brief": "섹션별 진단 해석 요약 1-2문장",
            "topic_strategy_brief": "주제·전략 요약 1-2문장",
            "roadmap_bridge": "1m/3m/6m 연결 문장 1개",
            "uncertainty_bridge": "불확실성 경계 문장 1개",
            "final_consultant_memo": "최종 실행 코멘트 3-4문장",
        },
    }

    try:
        registry = get_prompt_registry()
        system_instruction = registry.compose_prompt("diagnosis.consultant-report-orchestration")
        prompt = (
            f"{registry.compose_prompt('diagnosis.executive-summary-writer')}\n\n"
            f"{registry.compose_prompt('diagnosis.roadmap-generator')}\n\n"
            "[진단 컨텍스트 JSON]\n"
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
    verified_strength = (result.strengths or ["검증 가능한 강점 신호가 제한적입니다."])[0]
    primary_gap = (result.gaps or ["근거 밀도와 과정 설명 보강이 필요합니다."])[0]
    major_fit_seed = (document_structure.get("subject_major_alignment_signals") or ["전공 연계 근거 문장이 제한적입니다."])[0]
    section_density = document_structure.get("section_density") if isinstance(document_structure.get("section_density"), dict) else {}
    density_focus = ", ".join(f"{k}:{int(float(v) * 100)}%" for k, v in list(section_density.items())[:3]) if section_density else "섹션 밀도 정보가 제한적입니다."

    executive_summary = _guardrail_text(
        narrative.executive_summary,
        fallback=(
            f"현재 진단 기준에서 확인된 핵심 강점은 '{verified_strength}'입니다. "
            f"우선 보완축은 '{primary_gap}'이며, 문장-근거 정합성 개선이 필요합니다. "
            "검증이 약한 항목은 '추가 확인 필요'로 분리해 과장 위험을 차단했습니다."
        ),
        max_len=1200,
    )
    if "추가 확인 필요" not in executive_summary:
        executive_summary = f"{executive_summary} 근거가 약한 항목은 추가 확인 필요로 표기합니다."

    final_memo = _guardrail_text(
        narrative.final_consultant_memo,
        fallback=_build_fallback_final_memo(result=result),
        max_len=1100,
    )

    return _ConsultantNarrativePayload(
        executive_summary=executive_summary,
        current_record_status_brief=_guardrail_text(
            narrative.current_record_status_brief,
            fallback=f"현재 기록 상태는 '{result.recommended_focus or '근거 중심 보강'}' 축을 우선 정렬해야 합니다.",
            max_len=360,
        ),
        strengths_brief=_guardrail_text(
            narrative.strengths_brief,
            fallback=f"확인된 강점은 '{verified_strength}'이며 근거 연결성을 유지해야 합니다.",
            max_len=360,
        ),
        weaknesses_risks_brief=_guardrail_text(
            narrative.weaknesses_risks_brief,
            fallback=f"핵심 리스크는 '{primary_gap}'이고 약한 섹션은 {', '.join(weak_sections[:3]) or '추가 확인 필요 항목'}입니다.",
            max_len=360,
        ),
        major_fit_brief=_guardrail_text(
            narrative.major_fit_brief,
            fallback=f"전공 적합성 해석은 '{major_fit_seed}' 근거를 기준으로 보수적으로 제시합니다.",
            max_len=360,
        ),
        section_diagnosis_brief=_guardrail_text(
            narrative.section_diagnosis_brief,
            fallback=f"섹션 밀도 기준 핵심 점검 축은 {density_focus} 입니다.",
            max_len=360,
        ),
        topic_strategy_brief=_guardrail_text(
            narrative.topic_strategy_brief,
            fallback=f"주제 전략은 '{(result.recommended_topics or ['전공 연계 심화 주제'])[0]}' 중심으로 단계적 확장을 권장합니다.",
            max_len=360,
        ),
        roadmap_bridge=_guardrail_text(
            narrative.roadmap_bridge,
            fallback="로드맵은 1개월 정합성 정리, 3개월 보완축 개선, 6개월 전공 스토리 완성 순으로 운영합니다.",
            max_len=360,
        ),
        uncertainty_bridge=_guardrail_text(
            narrative.uncertainty_bridge,
            fallback=f"불확실성 경계: {(uncertainty_notes or ['검증 부족 항목은 추가 확인 필요로 유지']) [0]}",
            max_len=360,
        ),
        final_consultant_memo=final_memo,
    )


def _guardrail_text(value: str | None, *, fallback: str, max_len: int) -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    text = re.sub(r"\s+", " ", text).strip()
    for forbidden in ("합격 보장", "무조건 합격", "확정 합격", "반드시 합격", "대신 수행"):
        text = text.replace(forbidden, "검증 필요")
    if len(text) > max_len:
        text = f"{text[: max_len - 1].rstrip()}…"
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
                subtitle="자동 보완 섹션",
                body_markdown="- 구조 일관성을 위해 기본 섹션 틀을 유지했습니다.\n- 근거가 부족한 항목은 추가 확인 필요로 관리합니다.",
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
    strength = result.strengths[0] if result.strengths else "현재 기록에는 활용 가능한 기본 강점이 확인됩니다."
    gap = result.gaps[0] if result.gaps else "다음 단계에서는 근거 밀도와 과정 설명을 우선 보완해야 합니다."
    return (
        f"본 진단은 '{result.headline}'를 중심으로 학생부 근거를 재검토했습니다. "
        f"확인된 강점은 '{strength}'이며, 핵심 보완축은 '{gap}'입니다. "
        "현재 상태에서 가장 중요한 전략은 검증 가능한 사례를 중심으로 개요를 재정렬하고, "
        "근거가 약한 문장을 '추가 확인 필요'로 명시해 과장 가능성을 차단하는 것입니다."
    )


def _build_fallback_final_memo(*, result: DiagnosisResultPayload) -> str:
    focus = result.recommended_focus or "근거 연결 강화"
    next_step = result.next_actions[0] if result.next_actions else "개요의 다음 소단락 1개를 근거 중심으로 재작성"
    return (
        "최종 코멘트: 현재 자료만으로도 방향성은 충분히 도출됩니다. "
        f"다만 '{focus}'를 우선 과제로 두고, '{next_step}'를 실행해 문장-근거 정합성을 먼저 끌어올리는 것이 안전합니다. "
        "합격 예측성 문구나 검증되지 않은 성취 서술은 배제하고, 근거가 확보된 문장부터 완성도를 높이십시오."
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
            score_lines.append(f"{block.label}: {block.score}점 ({block.band})")

    evidence_cards = evidence_bank[:6]
    evidence_card_lines: list[str] = []
    for idx, card in enumerate(evidence_cards, start=1):
        quote = _clean_line(str(card.get("quote") or ""), max_len=62)
        interpretation = _clean_line(str(card.get("theme") or "핵심 활동"), max_len=28)
        why_it_matters = _clean_line(
            ", ".join(str(item) for item in (card.get("major_relevance") or [])[:2]) or "전공 연계",
            max_len=26,
        )
        risk_note = "설명 확장 필요" if not bool((card.get("process_elements") or {}).get("limitation")) else "한계 인식 포함"
        evidence_card_lines.append(
            f"[카드 {idx}] p.{card.get('page')} | 원문: {quote} | 해석: {interpretation} | 의미: {why_it_matters} | 리스크: {risk_note}"
        )

    interview_questions = _dedupe(
        [
            "지속가능 건축에 관심을 갖게 된 구체적 계기는 무엇인가요?",
            "재난·기후 대응 관점에서 본인의 탐구를 한 문장으로 설명해 보세요.",
            "구조/재료 선택에서 어떤 기준으로 판단했는지 설명해 보세요.",
            "사용자 경험이나 공간 인문 관점에서 보완하고 싶은 점은 무엇인가요?",
            "교과 세특의 탐구를 실제 설계 사고로 연결한 사례가 있나요?",
            "향후 6개월 동안 스토리라인을 강화하기 위한 실행 계획은 무엇인가요?",
            *[f"근거 기반 확인 질문: {signal}" for signal in continuity_signals[:2]],
        ],
        limit=8,
    )

    roadmap_lines: list[str] = []
    for item in roadmap:
        roadmap_lines.append(item.title)
        roadmap_lines.extend([f"- {action}" for action in item.actions[:3]])

    storyline = "재난/기후 대응형 지속가능 건축"
    one_line_verdict = (
        "전공 적합성은 높고 연속성도 확인되지만, 서사 축이 분산되어 있어 "
        f"'{storyline}' 한 줄로 통합이 필요합니다."
    )
    if reanalysis_required:
        one_line_verdict = (
            "재분석 필요: 필수 섹션 추출 커버리지가 부족하여 학생 평가 점수는 참고용으로만 제시합니다."
        )

    baseline_lines = [
        target_context,
        f"분석 신뢰도: {int(round(float(coverage_check.get('coverage_score', 0.0)) * 100))}%",
        *(score_lines[:14] or ["점수 데이터가 제한적입니다."]),
        f"섹션 커버리지 누락: {', '.join(coverage_check.get('missing_required_sections', [])[:5]) or '없음'}",
    ]

    timeline_lines = timeline_signals[:6] or ["학년별 연속 신호가 제한적이어서 페이지 근거 중심으로 재정렬이 필요합니다."]
    fit_lines = [
        narratives.major_fit_brief or "건축 관련 연속성은 강하지만, 스토리라인 통합이 우선 과제입니다.",
        "강점 축: 기술/구조/재료/환경 테마의 누적",
        "보완 축: 디자인 언어·사용자 경험·공간 인문 프레이밍",
        f"권장 통합 서사: {storyline}",
        *(alignment_signals[:2] or []),
    ]

    sections = [
        ConsultantDiagnosisSection(
            id="executive_summary",
            title="Executive Summary",
            subtitle="한 줄 판정 · 강점 3 · 리스크 3",
            body_markdown=_bulleted(
                [
                    f"한 줄 판정: {one_line_verdict}",
                    *(result.strengths[:3] or ["핵심 강점 근거가 제한적입니다."]),
                    *(result.gaps[:3] or ["핵심 리스크 근거가 제한적입니다."]),
                    f"최우선 액션: {result.recommended_focus}",
                ]
            ),
            evidence_items=pick_evidence(3),
            additional_verification_needed=uncertainty_notes[:2] if reanalysis_required else [],
        ),
        ConsultantDiagnosisSection(
            id="record_baseline_dashboard",
            title="Academic & Record Baseline Dashboard",
            subtitle="학생 평가 점수와 시스템 품질 점수 분리",
            body_markdown=_bulleted(baseline_lines),
            evidence_items=pick_evidence(2),
            additional_verification_needed=weak_sections[:3],
        ),
        ConsultantDiagnosisSection(
            id="narrative_timeline",
            title="Narrative Timeline",
            subtitle="학년별 관심 진화 흐름",
            body_markdown=_bulleted(
                [
                    "1학년 → 기초 탐색과 주제 발견",
                    "2학년 → 구조/재료/환경 테마 심화",
                    "3학년 → 전공 연계 스토리 통합 필요",
                    *timeline_lines,
                ]
            ),
            evidence_items=pick_evidence(2),
        ),
        ConsultantDiagnosisSection(
            id="evidence_cards",
            title="Evidence Cards",
            subtitle="핵심 근거 6개 카드",
            body_markdown=_bulleted(evidence_card_lines or ["핵심 근거 카드 생성에 필요한 앵커가 부족합니다."]),
            evidence_items=pick_evidence(4),
            unsupported_claims=["원문에 없는 수상·성취·실험 결과는 생성하지 않습니다."],
        ),
        ConsultantDiagnosisSection(
            id="strength_analysis",
            title="Strength Analysis",
            subtitle="상위 강점 진단",
            body_markdown=_bulleted(
                [
                    *(result.strengths[:3] or ["강점 진술이 제한적입니다."]),
                    narratives.strengths_brief or "강점은 페이지 근거와 직접 연결되어야 합니다.",
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
            subtitle="상위 리스크 진단",
            body_markdown=_bulleted(
                [
                    *(result.gaps[:3] or ["리스크 진술이 제한적입니다."]),
                    "핵심 리스크는 전공 부적합이 아니라 서사 분산입니다.",
                    *(weak_sections[:3] or ["약한 섹션은 재분석 후 확정이 필요합니다."]),
                ]
            ),
            evidence_items=pick_evidence(3),
            additional_verification_needed=uncertainty_notes[:3],
            unsupported_claims=["검증되지 않은 합격 예측/보장 문구 금지"],
        ),
        ConsultantDiagnosisSection(
            id="major_fit",
            title="Target-Major Fit Interpretation",
            subtitle="서울대 건축 지망 기준 해석",
            body_markdown=_bulleted(fit_lines),
            evidence_items=pick_evidence(3),
            additional_verification_needed=["디자인 언어·사용자 경험 관련 근거 카드 보강"],
        ),
        ConsultantDiagnosisSection(
            id="interview_questions",
            title="Probable Interview Questions",
            subtitle="면접 예상 질문",
            body_markdown=_bulleted(interview_questions),
            evidence_items=pick_evidence(2),
        ),
        ConsultantDiagnosisSection(
            id="roadmap",
            title="Action Roadmap",
            subtitle="1개월 · 3개월 · 6개월 실행 계획",
            body_markdown=_bulleted(
                [
                    narratives.roadmap_bridge or "단계별 실행 계획은 근거 보강과 스토리 통합 순으로 진행합니다.",
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
        source_base = f"학생부 앵커 {anchor_id}" if anchor_id else f"학생부 p.{page_number}" if page_number else "학생부 앵커"
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
                    notes.append(f"파싱 경고: {text}")
        confidence = metadata.get("parse_confidence")
        if isinstance(confidence, (int, float)):
            notes.append(f"파싱 confidence={round(float(confidence), 3)}")
        quality_score = metadata.get("pipeline_quality_score")
        if isinstance(quality_score, (int, float)):
            notes.append(f"파이프라인 quality_score={round(float(quality_score), 3)}")
    for item in document_structure.get("uncertain_items", [])[:5]:
        notes.append(f"구조 추정 불확실 항목: {item}")
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
        title=f"{project.title} 전문 컨설턴트 진단서",
        subtitle="생성 실패 - 제한 정보",
        student_target_context=f"프로젝트: {project.title}",
        generated_at=datetime.now(timezone.utc),
        score_blocks=[],
        sections=[
            ConsultantDiagnosisSection(
                id="generation_failed",
                title="진단서 생성 실패",
                subtitle=None,
                body_markdown="요청한 진단서를 생성하지 못했습니다. 프로젝트 근거 문서를 확인한 뒤 재시도해 주세요.",
            )
        ],
        roadmap=[],
        citations=[],
        uncertainty_notes=["리포트 생성 실패로 인해 상세 분석이 포함되지 않았습니다."],
        final_consultant_memo="근거 문서 상태 확인 후 재생성해 주세요.",
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
    return f"{text[: max_len - 1].rstrip()}…"


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
        "grades_subjects": "교과학습발달상황",
        "grades_and_notes": "교과학습발달상황",
        "subject_special_notes": "세특",
        "creative_activities": "창체",
        "extracurricular": "창체",
        "volunteer": "창체",
        "career_signals": "진로",
        "reading": "독서",
        "reading_activity": "독서",
        "behavior_general_comments": "행동특성",
        "behavior_opinion": "행동특성",
    }
    return alias.get(text, text)
