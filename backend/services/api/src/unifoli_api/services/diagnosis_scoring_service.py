from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from unifoli_api.services.student_record_feature_service import StudentRecordFeatures

AdmissionAxisKey = Literal[
    "major_alignment",
    "inquiry_continuity",
    "evidence_density",
    "process_explanation",
    "authenticity_risk",
]
RiskLevel = Literal["safe", "warning", "danger"]


class AxisSemanticGrade(BaseModel):
    score: int = Field(ge=0, le=100)
    rationale: str
    evidence_hints: list[str] = Field(default_factory=list)


class SemanticDiagnosisExtraction(BaseModel):
    major_alignment: AxisSemanticGrade
    inquiry_continuity: AxisSemanticGrade
    evidence_density: AxisSemanticGrade
    process_explanation: AxisSemanticGrade
    summary_insight: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)

_SECTION_LABELS: dict[str, str] = {
    "êµê³¼?™ìŠµë°œë‹¬?í™©": "êµê³¼?™ìŠµë°œë‹¬?í™©",
    "ì°½ì˜?ì²´?˜í™œ??: "ì°½ì˜?ì²´?˜í™œ??,
    "?‰ë™?¹ì„± ë°?ì¢…í•©?˜ê²¬": "?‰ë™?¹ì„± ë°?ì¢…í•©?˜ê²¬",
    "?…ì„œ?œë™": "?…ì„œ?œë™",
    "?˜ìƒê²½ë ¥": "?˜ìƒê²½ë ¥",
}
_POSITIVE_AXIS_LABELS: dict[str, str] = {
    "major_alignment": "?„ê³µ ?í•©??,
    "inquiry_continuity": "?êµ¬ ?°ì†??,
    "evidence_density": "ì¦ê±° ë°€??,
    "process_explanation": "ê³¼ì • ?¤ëª…??,
}


class AdmissionAxisResult(BaseModel):
    key: AdmissionAxisKey
    label: str
    score: int = Field(ge=0, le=100)
    band: str
    severity: Literal["low", "medium", "high"]
    rationale: str
    evidence_hints: list[str] = Field(default_factory=list)


class SectionAnalysisItem(BaseModel):
    key: str
    label: str
    present: bool
    record_count: int = Field(ge=0)
    note: str


class DocumentQualitySummary(BaseModel):
    source_mode: str
    parse_reliability_score: int = Field(ge=0, le=100)
    parse_reliability_band: str
    needs_review: bool
    needs_review_documents: int = Field(ge=0)
    total_records: int = Field(ge=0)
    total_word_count: int = Field(ge=0)
    narrative_density: float = Field(ge=0.0, le=1.0)
    evidence_density: float = Field(ge=0.0, le=1.0)
    summary: str


class DiagnosisScoringSheet(BaseModel):
    overview: str
    document_quality: DocumentQualitySummary
    section_analysis: list[SectionAnalysisItem] = Field(default_factory=list)
    admission_axes: list[AdmissionAxisResult] = Field(default_factory=list)
    strengths_candidates: list[str] = Field(default_factory=list)
    gap_candidates: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    next_action_seeds: list[str] = Field(default_factory=list)
    recommended_topics: list[str] = Field(default_factory=list)
    risk_level: RiskLevel
    recommended_focus: str


async def extract_semantic_diagnosis(
    *,
    masked_text: str,
    target_major: str | None,
    target_university: str | None,
    interest_universities: list[str] | None = None,
) -> SemanticDiagnosisExtraction:
    from unifoli_api.core.llm import get_llm_client
    
    llm = get_llm_client()
    # Force use a faster model for scoring to keep latency low
    if hasattr(llm, "model_name"):
        llm.model_name = "gemini-1.5-flash"
        
    interest_context = ""
    if interest_universities:
        interest_context = f". Other Interest Universities: {', '.join(interest_universities)}"

    system_instruction = (
        "You are an expert admissions officer. Extract semantic scores for the student record axes. "
        "Each axis score should reflect the DEPTH and QUALITY of the record, not just the presence of text. "
        f"Target Major: {target_major or 'General'}. Target University: {target_university or 'General'}{interest_context}. "
        "Be critical but fair. Provide specific evidence hints for each axis."
    )
    
    prompt = (
        "Analyze the following student record and extract strategic semantic scores.\n\n"
        f"=== Student Record ===\n{masked_text[:15000]}\n\n"
        "Return the analysis as JSON aligned to SemanticDiagnosisExtraction schema."
    )
    
    return await llm.generate_json(
        prompt=prompt,
        response_model=SemanticDiagnosisExtraction,
        system_instruction=system_instruction,
        temperature=0.1,
    )


def build_diagnosis_scoring_sheet(
    *,
    features: StudentRecordFeatures,
    project_title: str,
    target_major: str | None,
    target_university: str | None,
    interest_universities: list[str] | None = None,
    semantic: SemanticDiagnosisExtraction | None = None,
) -> DiagnosisScoringSheet:
    section_analysis = _build_section_analysis(features)
    document_quality = _build_document_quality(features)
    admission_axes = _build_admission_axes(features, semantic=semantic)
    risk_level = _derive_risk_level(admission_axes=admission_axes)

    strengths = _build_strengths(features=features, admission_axes=admission_axes, semantic=semantic)
    gaps = _build_gaps(features=features, admission_axes=admission_axes, semantic=semantic)
    risk_flags = _build_risk_flags(features=features, admission_axes=admission_axes)
    next_actions = _build_next_action_seeds(
        features=features,
        admission_axes=admission_axes,
        target_major=target_major,
    )
    recommended_topics = _build_recommended_topics(features=features, target_major=target_major)

    weakest_axis = min(
        (axis for axis in admission_axes if axis.key != "authenticity_risk"),
        key=lambda axis: axis.score,
        default=None,
    )
    weakest_label = weakest_axis.label if weakest_axis else "?µì‹¬ ?‰ê?ì¶?
    
    # Construct multi-university context
    targets = []
    if target_university:
        targets.append(f"{target_university} {target_major or ''}".strip())
    if interest_universities:
        targets.extend(interest_universities)
    
    target_context = " ë°?".join(targets[:2]) + (f" ??{len(targets)-2}ê³? if len(targets) > 2 else "")
    if not target_context:
        target_context = target_major or "ëª©í‘œ ?„ê³µ"

    overview = (
        f"{project_title} ê¸°ì??¼ë¡œ ë¬¸ì„œ ? ë¢°?„ëŠ” {document_quality.parse_reliability_band} ?˜ì??´ë©°, "
        f"?„ìž¬??{weakest_label} ë³´ê°•???°ì„ ?…ë‹ˆ??"
    )
    recommended_focus = (
        f"{target_context} ì§€??ë§¥ë½?ì„œ {weakest_label}??ë¨¼ì? ë³´ê°•?˜ì„¸?? "
        "?ìˆ˜???„ìž¬ ê¸°ë¡ ê·¼ê±°ë¥?ê¸°ì??¼ë¡œ ê²°ì •ë¡ ì ?¼ë¡œ ê³„ì‚°?˜ì—ˆ?µë‹ˆ??"
    )

    return DiagnosisScoringSheet(
        overview=overview,
        document_quality=document_quality,
        section_analysis=section_analysis,
        admission_axes=admission_axes,
        strengths_candidates=strengths,
        gap_candidates=gaps,
        risk_flags=risk_flags,
        next_action_seeds=next_actions,
        recommended_topics=recommended_topics,
        risk_level=risk_level,
        recommended_focus=recommended_focus,
    )


def _build_section_analysis(features: StudentRecordFeatures) -> list[SectionAnalysisItem]:
    rows: list[SectionAnalysisItem] = []
    for key, label in _SECTION_LABELS.items():
        present = bool(features.section_presence.get(key))
        count = int(features.section_record_counts.get(key) or 0)
        if present and count >= 3:
            note = "ê¸°ë¡ ?˜ê? ì¶©ë¶„???¬í™” ê·¼ê±°ë¡??œìš© ê°€?¥í•©?ˆë‹¤."
        elif present:
            note = "ê¸°ë¡?€ ì¡´ìž¬?˜ì?ë§??˜ê? ?ì–´ ë³´ê°• ?¬ì?ê°€ ?ˆìŠµ?ˆë‹¤."
        else:
            note = "?´ë‹¹ ?¹ì…˜ ê¸°ë¡???•ì¸?˜ì? ?Šì•„ ë³´ê°•???„ìš”?©ë‹ˆ??"
        rows.append(
            SectionAnalysisItem(
                key=key,
                label=label,
                present=present,
                record_count=max(0, count),
                note=note,
            )
        )
    return rows


def _build_document_quality(features: StudentRecordFeatures) -> DocumentQualitySummary:
    reliability_score = _bounded_int(features.reliability_score * 100.0)
    if reliability_score >= 80:
        reliability_band = "?’ìŒ"
    elif reliability_score >= 60:
        reliability_band = "ë³´í†µ"
    else:
        reliability_band = "ì£¼ì˜"

    summary = (
        f"{features.document_count}ê°?ë¬¸ì„œ, ì´?{features.total_records}ê°??ˆì½”??ê¸°ì? "
        f"?Œì‹± ? ë¢°??{reliability_score}?ìœ¼ë¡??‰ê??ˆìŠµ?ˆë‹¤."
    )
    return DocumentQualitySummary(
        source_mode=features.source_mode,
        parse_reliability_score=reliability_score,
        parse_reliability_band=reliability_band,
        needs_review=features.needs_review,
        needs_review_documents=features.needs_review_documents,
        total_records=max(0, features.total_records),
        total_word_count=max(0, features.total_word_count),
        narrative_density=_clamp(features.narrative_density),
        evidence_density=_clamp(features.evidence_density),
        summary=summary,
    )


def _build_admission_axes(features: StudentRecordFeatures, semantic: SemanticDiagnosisExtraction | None = None) -> list[AdmissionAxisResult]:
    # 1. Base Heuristic Scores (Deterministic)
    h_major_alignment = _bounded_int(
        20
        + features.major_term_overlap_ratio * 58
        + min(features.unique_subject_count, 10) * 2.8
        + (8 if features.section_presence.get("êµê³¼?™ìŠµë°œë‹¬?í™©") else 0)
    )
    h_inquiry_continuity = _bounded_int(
        24
        + features.repeated_subject_ratio * 52
        + min(features.total_records, 40) * 0.9
        + (6 if features.section_presence.get("ì°½ì˜?ì²´?˜í™œ??) else 0)
    )
    h_evidence_density = _bounded_int(
        20
        + features.evidence_density * 56
        + min(features.evidence_reference_count, 25) * 1.0
    )
    h_process_explanation = _bounded_int(
        22
        + features.narrative_density * 60
        + min(features.section_record_counts.get("?‰ë™?¹ì„± ë°?ì¢…í•©?˜ê²¬", 0), 8) * 2.0
    )
    
    # 2. Merge with Semantic Data (LLM Semantic extraction has 70% weight if available)
    def _merge(h_score: int, s_grade: AxisSemanticGrade | None) -> tuple[int, str, list[str]]:
        if not s_grade:
            return h_score, "", []
        # Semantic score is more "intelligent", so we weigh it heavily
        final_score = _bounded_int(h_score * 0.3 + s_grade.score * 0.7)
        return final_score, s_grade.rationale, s_grade.evidence_hints

    s_major = semantic.major_alignment if semantic else None
    s_inquiry = semantic.inquiry_continuity if semantic else None
    s_evidence = semantic.evidence_density if semantic else None
    s_process = semantic.process_explanation if semantic else None

    # Authenticity risk calculation (Higher is riskier)
    authenticity_risk = _bounded_int(
        78
        - features.reliability_score * 44
        - features.evidence_density * 20
        - features.repeated_subject_ratio * 10
        + (16 if features.needs_review else 0)
        + (10 if features.total_records < 5 else 0)
    )

    axes: list[AdmissionAxisResult] = []
    
    # Axis 1: Major Alignment
    score, rationale, hints = _merge(h_major_alignment, s_major)
    axes.append(
        _positive_axis(
            key="major_alignment",
            score=score,
            rationale=rationale or _major_alignment_rationale(score),
            hints=hints or [
                f"?„ê³µ ?¤ì›Œ??ì¤‘ì²© ë¹„ìœ¨: {round(features.major_term_overlap_ratio, 3)}",
                f"ê³ ìœ  ê³¼ëª© ?? {features.unique_subject_count}",
            ],
        )
    )
    
    # Axis 2: Inquiry Continuity
    score, rationale, hints = _merge(h_inquiry_continuity, s_inquiry)
    axes.append(
        _positive_axis(
            key="inquiry_continuity",
            score=score,
            rationale=rationale or _inquiry_rationale(score),
            hints=hints or [
                f"ë°˜ë³µ ê³¼ëª© ë¹„ìœ¨: {round(features.repeated_subject_ratio, 3)}",
                f"ì´??ˆì½”???? {features.total_records}",
            ],
        )
    )
    
    # Axis 3: Evidence Density
    score, rationale, hints = _merge(h_evidence_density, s_evidence)
    axes.append(
        _positive_axis(
            key="evidence_density",
            score=score,
            rationale=rationale or _evidence_rationale(score),
            hints=hints or [
                f"ì¦ê±° ë°€?? {round(features.evidence_density, 3)}",
                f"ì¦ê±° ì°¸ì¡° ?? {features.evidence_reference_count}",
            ],
        )
    )
    
    # Axis 4: Process Explanation
    score, rationale, hints = _merge(h_process_explanation, s_process)
    axes.append(
        _positive_axis(
            key="process_explanation",
            score=score,
            rationale=rationale or _process_rationale(score),
            hints=hints or [
                f"?œìˆ  ë°€?? {round(features.narrative_density, 3)}",
                f"?‰ë™?¹ì„±/ì¢…í•©?˜ê²¬ ?ˆì½”?? {features.section_record_counts.get('?‰ë™?¹ì„± ë°?ì¢…í•©?˜ê²¬', 0)}",
            ],
        )
    )
    
    axes.append(
        _authenticity_risk_axis(
            score=authenticity_risk,
            hints=[
                f"?Œì‹± ? ë¢°?? {round(features.reliability_score, 3)}",
                f"needs_review ë¬¸ì„œ ?? {features.needs_review_documents}",
            ],
        )
    )
    return axes


def _positive_axis(
    *,
    key: Literal["major_alignment", "inquiry_continuity", "evidence_density", "process_explanation"],
    score: int,
    rationale: str,
    hints: list[str],
) -> AdmissionAxisResult:
    if score >= 80:
        band = "strong"
        severity: Literal["low", "medium", "high"] = "low"
    elif score >= 60:
        band = "watch"
        severity = "medium"
    else:
        band = "weak"
        severity = "high"
    return AdmissionAxisResult(
        key=key,
        label=_POSITIVE_AXIS_LABELS[key],
        score=score,
        band=band,
        severity=severity,
        rationale=rationale,
        evidence_hints=hints,
    )


def _authenticity_risk_axis(*, score: int, hints: list[str]) -> AdmissionAxisResult:
    if score <= 35:
        band = "stable"
        severity: Literal["low", "medium", "high"] = "low"
        rationale = "ê·¼ê±° ?€ë¹?ê³¼ìž¥ ?„í—˜????³  ê¸°ë¡ ?¼ê??±ì´ ? ì??©ë‹ˆ??"
    elif score <= 60:
        band = "watch"
        severity = "medium"
        rationale = "?¼ë? êµ¬ê°„?ì„œ ê·¼ê±° ë°€?„ì? ?¤ëª… ?¼ê??±ì„ ì¶”ê? ?•ì¸?´ì•¼ ?©ë‹ˆ??"
    else:
        band = "high_risk"
        severity = "high"
        rationale = "ê·¼ê±° ?€ë¹?ì£¼ìž¥ ê³¼ìž¥ ê°€?¥ì„±???ˆì–´ ë³´ìˆ˜???œìˆ ê³?ì¦ê±° ë³´ê°•???„ìš”?©ë‹ˆ??"
    return AdmissionAxisResult(
        key="authenticity_risk",
        label="ì§„ì •?±Â·ê³¼???„í—˜",
        score=score,
        band=band,
        severity=severity,
        rationale=rationale,
        evidence_hints=hints,
    )


def _major_alignment_rationale(score: int) -> str:
    if score >= 80:
        return "?„ê³µ ?°ê³„ ?¤ì›Œ?œì? ê³¼ëª© ë¶„í¬ê°€ ë¹„êµ???ˆì •?ìœ¼ë¡??°ê²°?©ë‹ˆ??"
    if score >= 60:
        return "?„ê³µ ?°ê³„ ?¨ì„œ???ˆìœ¼??ê¸°ë¡ ?„ë°˜?ì„œ ë°˜ë³µ ?¸ì¶œ?????„ìš”?©ë‹ˆ??"
    return "?„ê³µ ?°ê²° ? í˜¸ê°€ ?½í•´ ?µì‹¬ ê³¼ëª©/?œë™ ê·¼ê±°ë¥?ëª…ì‹œ?ìœ¼ë¡?ë³´ê°•?´ì•¼ ?©ë‹ˆ??"


def _inquiry_rationale(score: int) -> str:
    if score >= 80:
        return "?êµ¬ ?ë¦„???¨ë°œ?±ì´ ?„ë‹ˆ???„ì† ?œë™?¼ë¡œ ?´ì–´ì§€???¨í„´???•ì¸?©ë‹ˆ??"
    if score >= 60:
        return "?êµ¬ ?°ì†???¨ì„œê°€ ?¼ë? ?ˆìœ¼??ê³¼ëª©/ì£¼ì œ ?¬ë“±???ë¦„????ëª…í™•???´ì•¼ ?©ë‹ˆ??"
    return "?œë™???¨íŽ¸?ìœ¼ë¡?ë³´ì¼ ???ˆì–´ ë¹„êµÂ·?„ì†Â·?¬í™” ?ë¦„???˜ë„?ìœ¼ë¡??°ê²°?´ì•¼ ?©ë‹ˆ??"


def _evidence_rationale(score: int) -> str:
    if score >= 80:
        return "?˜ì¹˜/ê´€ì°?ê¸°ë¡ ê·¼ê±°ê°€ ì¶©ë¶„??ì£¼ìž¥??ë°©ì–´?˜ê¸° ì¢‹ìŠµ?ˆë‹¤."
    if score >= 60:
        return "?µì‹¬ ê·¼ê±°???ˆìœ¼??ì£¼ìž¥ ?€ë¹?ì¦ê±° ë°€?„ë? ???¨ê³„ ???’ì¼ ?„ìš”ê°€ ?ˆìŠµ?ˆë‹¤."
    return "ê·¼ê±° ë°€?„ê? ??•„ ê²°ê³¼ ì£¼ìž¥ë³´ë‹¤ ê´€ì°??¬ì‹¤??ë¨¼ì? ì¶•ì ?˜ëŠ” ê²ƒì´ ?ˆì „?©ë‹ˆ??"


def _process_rationale(score: int) -> str:
    if score >= 80:
        return "ê³¼ì • ?¤ëª…ê³?ë°˜ì„± ê¸°ë¡??ë¹„êµ??êµ¬ì²´?ìœ¼ë¡??œëŸ¬?©ë‹ˆ??"
    if score >= 60:
        return "ê³¼ì • ?œìˆ ?€ ?ˆìœ¼??ë°©ë²•-?œê³„-ê°œì„ ???°ê²°?????ë ·?˜ê²Œ ?ì–´???©ë‹ˆ??"
    return "ë¬´ì—‡???ˆëŠ”ì§€??ë³´ì´ì§€ë§???ê·¸ë ‡ê²??ˆëŠ”ì§€?€ ?œê³„ ?¤ëª…??ë¶€ì¡±í•©?ˆë‹¤."


def _derive_risk_level(*, admission_axes: list[AdmissionAxisResult]) -> RiskLevel:
    positive_axes = [axis for axis in admission_axes if axis.key != "authenticity_risk"]
    weak_count = sum(1 for axis in positive_axes if axis.band == "weak")
    watch_count = sum(1 for axis in positive_axes if axis.band == "watch")
    authenticity = next((axis for axis in admission_axes if axis.key == "authenticity_risk"), None)
    authenticity_score = authenticity.score if authenticity else 50

    if authenticity_score >= 70 or weak_count >= 2:
        return "danger"
    if authenticity_score >= 50 or weak_count >= 1 or watch_count >= 2:
        return "warning"
    return "safe"


def _build_strengths(
    *,
    features: StudentRecordFeatures,
    admission_axes: list[AdmissionAxisResult],
    semantic: SemanticDiagnosisExtraction | None = None,
) -> list[str]:
    strengths: list[str] = []
    if semantic and semantic.strengths:
        strengths.extend(semantic.strengths)
        
    for axis in admission_axes:
        if axis.key == "authenticity_risk":
            continue
        if axis.band == "strong":
            strengths.append(f"{axis.label}: {axis.rationale}")
    if features.section_presence.get("êµê³¼?™ìŠµë°œë‹¬?í™©") and features.section_record_counts.get("êµê³¼?™ìŠµë°œë‹¬?í™©", 0) >= 3:
        strengths.append("êµê³¼?™ìŠµë°œë‹¬?í™© ê¸°ë¡?‰ì´ ì¶©ë¶„???™ì—… ê·¼ê±° ?œì‹œ??? ë¦¬?©ë‹ˆ??")
    if not strengths:
        strengths.append("?µì‹¬ ?¹ì…˜??ê¸°ë°˜?¼ë¡œ ?•ìž¥ ê°€?¥í•œ ìµœì†Œ ê·¼ê±°???•ë³´?˜ì–´ ?ˆìŠµ?ˆë‹¤.")
    return _dedupe_keep_order(strengths)[:8]


def _build_gaps(
    *,
    features: StudentRecordFeatures,
    admission_axes: list[AdmissionAxisResult],
    semantic: SemanticDiagnosisExtraction | None = None,
) -> list[str]:
    gaps: list[str] = []
    if semantic and semantic.gaps:
        gaps.extend(semantic.gaps)
        
    for axis in admission_axes:
        if axis.key == "authenticity_risk":
            continue
        if axis.band in {"weak", "watch"}:
            gaps.append(f"{axis.label}: {axis.rationale}")
    for section_key, present in features.section_presence.items():
        if not present and section_key in _SECTION_LABELS:
            gaps.append(f"{section_key} ?¹ì…˜ ê·¼ê±°ê°€ ë¶€ì¡±í•©?ˆë‹¤.")
    if not gaps:
        gaps.append("?„ìž¬ êµ¬ì¡°ë¥?? ì??˜ë©´???¸ë? ì¦ê±°(?˜ì¹˜, ë¹„êµ, ë°˜ì„±)ë¥?ì¶”ê??˜ë©´ ?„ì„±?„ê? ?’ì•„ì§‘ë‹ˆ??")
    return _dedupe_keep_order(gaps)[:10]


def _build_risk_flags(
    *,
    features: StudentRecordFeatures,
    admission_axes: list[AdmissionAxisResult],
) -> list[str]:
    flags = list(features.risk_flags)
    authenticity = next((axis for axis in admission_axes if axis.key == "authenticity_risk"), None)
    if authenticity and authenticity.band == "high_risk":
        flags.append("ì§„ì •?±Â·ê³¼???„í—˜ ì¶•ì´ ?’ì•„ ?œí˜„ ?˜ìœ„ë¥?ë³´ìˆ˜?ìœ¼ë¡?? ì??´ì•¼ ?©ë‹ˆ??")
    return _dedupe_keep_order(flags)[:8]


def _build_next_action_seeds(
    *,
    features: StudentRecordFeatures,
    admission_axes: list[AdmissionAxisResult],
    target_major: str | None,
) -> list[str]:
    actions: list[str] = []
    weakest_positive = sorted(
        (axis for axis in admission_axes if axis.key != "authenticity_risk"),
        key=lambda axis: axis.score,
    )[:2]
    for axis in weakest_positive:
        if axis.key == "major_alignment":
            actions.append("?„ìž¬ ê¸°ë¡ ì¤??„ê³µ ê´€??ê³¼ëª©/?œë™ ë¬¸ìž¥????ë¬¸ë‹¨?¼ë¡œ ?¬ì •?¬í•´ ?°ê²°?±ì„ ëª…ì‹œ?˜ì„¸??")
        elif axis.key == "inquiry_continuity":
            actions.append("ê°™ì? ì£¼ì œë¥?2???´ìƒ ?´ì–´ì§€???ë¦„(ë¬¸ì œ-?œë„-ê°œì„ )?¼ë¡œ ?•ë¦¬?˜ì„¸??")
        elif axis.key == "evidence_density":
            actions.append("ì£¼ìž¥ë§ˆë‹¤ ê´€ì°?ê·¼ê±° 1ê°??´ìƒ???°ê²°?˜ê³  ?˜ì¹˜/?¬ì‹¤ ?œí˜„???°ì„  ë°°ì¹˜?˜ì„¸??")
        elif axis.key == "process_explanation":
            actions.append("ë°©ë²•-?œê³„-ê°œì„  ?œì„œë¡?ê³¼ì • ?¤ëª…??3ë¬¸ìž¥ ?´ìƒ ê³ ì • ?œí”Œë¦¿ìœ¼ë¡??‘ì„±?˜ì„¸??")

    if features.needs_review:
        actions.append("needs_review ?œì‹œ ë¬¸ì„œ???ë¬¸ ?€ì¡????µì‹¬ ë¬¸ìž¥??ë³´ìˆ˜?ìœ¼ë¡??¬ìž‘?±í•˜?¸ìš”.")
    if target_major:
        actions.append(f"{target_major} ì§€??ë§¥ë½??ë§žëŠ” ?œë™ 1ê°œë? ? ì •??ê·¼ê±° ì¤‘ì‹¬?¼ë¡œ ?¬í™” ê¸°ë¡??ì¶”ê??˜ì„¸??")
    return _dedupe_keep_order(actions)[:8]


def _build_recommended_topics(
    *,
    features: StudentRecordFeatures,
    target_major: str | None,
) -> list[str]:
    topics = [subject for subject, _ in features.subject_distribution.items()][:5]
    if target_major:
        topics.insert(0, f"{target_major} ?°ê³„ ?¬í™”?êµ¬")
    if not topics:
        topics = ["êµê³¼ ê¸°ë°˜ ?¬í™”?êµ¬", "ì§„ë¡œ ?°ê³„ ?„ë¡œ?íŠ¸", "ë¹„êµÂ·ë¶„ì„???œë™"]
    return _dedupe_keep_order(topics)[:6]


def _bounded_int(value: float) -> int:
    return int(max(0, min(100, round(value))))


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped
