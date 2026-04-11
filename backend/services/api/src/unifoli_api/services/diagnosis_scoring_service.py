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
    "援먭낵?숈뒿諛쒕떖?곹솴": "援먭낵?숈뒿諛쒕떖?곹솴",
    "李쎌쓽?곸껜?섑솢??: "李쎌쓽?곸껜?섑솢??,
    "?됰룞?뱀꽦 諛?醫낇빀?섍껄": "?됰룞?뱀꽦 諛?醫낇빀?섍껄",
    "?낆꽌?쒕룞": "?낆꽌?쒕룞",
    "?섏긽寃쎈젰": "?섏긽寃쎈젰",
}
_POSITIVE_AXIS_LABELS: dict[str, str] = {
    "major_alignment": "?꾧났 ?곹빀??,
    "inquiry_continuity": "?먭뎄 ?곗냽??,
    "evidence_density": "利앷굅 諛??,
    "process_explanation": "怨쇱젙 ?ㅻ챸??,
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
    weakest_label = weakest_axis.label if weakest_axis else "?듭떖 ?됯?異?
    
    # Construct multi-university context
    targets = []
    if target_university:
        targets.append(f"{target_university} {target_major or ''}".strip())
    if interest_universities:
        targets.extend(interest_universities)
    
    target_context = " 諛?".join(targets[:2]) + (f" ??{len(targets)-2}怨? if len(targets) > 2 else "")
    if not target_context:
        target_context = target_major or "紐⑺몴 ?꾧났"

    overview = (
        f"{project_title} 湲곗??쇰줈 臾몄꽌 ?좊ː?꾨뒗 {document_quality.parse_reliability_band} ?섏??대ŉ, "
        f"?꾩옱??{weakest_label} 蹂닿컯???곗꽑?낅땲??"
    )
    recommended_focus = (
        f"{target_context} 吏??留λ씫?먯꽌 {weakest_label}??癒쇱? 蹂닿컯?섏꽭?? "
        "?먯닔???꾩옱 湲곕줉 洹쇨굅瑜?湲곗??쇰줈 寃곗젙濡좎쟻?쇰줈 怨꾩궛?섏뿀?듬땲??"
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
            note = "湲곕줉 ?섍? 異⑸텇???ы솕 洹쇨굅濡??쒖슜 媛?ν빀?덈떎."
        elif present:
            note = "湲곕줉? 議댁옱?섏?留??섍? ?곸뼱 蹂닿컯 ?ъ?媛 ?덉뒿?덈떎."
        else:
            note = "?대떦 ?뱀뀡 湲곕줉???뺤씤?섏? ?딆븘 蹂닿컯???꾩슂?⑸땲??"
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
        reliability_band = "?믪쓬"
    elif reliability_score >= 60:
        reliability_band = "蹂댄넻"
    else:
        reliability_band = "二쇱쓽"

    summary = (
        f"{features.document_count}媛?臾몄꽌, 珥?{features.total_records}媛??덉퐫??湲곗? "
        f"?뚯떛 ?좊ː??{reliability_score}?먯쑝濡??됯??덉뒿?덈떎."
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
        + (8 if features.section_presence.get("援먭낵?숈뒿諛쒕떖?곹솴") else 0)
    )
    h_inquiry_continuity = _bounded_int(
        24
        + features.repeated_subject_ratio * 52
        + min(features.total_records, 40) * 0.9
        + (6 if features.section_presence.get("李쎌쓽?곸껜?섑솢??) else 0)
    )
    h_evidence_density = _bounded_int(
        20
        + features.evidence_density * 56
        + min(features.evidence_reference_count, 25) * 1.0
    )
    h_process_explanation = _bounded_int(
        22
        + features.narrative_density * 60
        + min(features.section_record_counts.get("?됰룞?뱀꽦 諛?醫낇빀?섍껄", 0), 8) * 2.0
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
                f"?꾧났 ?ㅼ썙??以묒꺽 鍮꾩쑉: {round(features.major_term_overlap_ratio, 3)}",
                f"怨좎쑀 怨쇰ぉ ?? {features.unique_subject_count}",
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
                f"諛섎났 怨쇰ぉ 鍮꾩쑉: {round(features.repeated_subject_ratio, 3)}",
                f"珥??덉퐫???? {features.total_records}",
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
                f"利앷굅 諛?? {round(features.evidence_density, 3)}",
                f"利앷굅 李몄“ ?? {features.evidence_reference_count}",
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
                f"?쒖닠 諛?? {round(features.narrative_density, 3)}",
                f"?됰룞?뱀꽦/醫낇빀?섍껄 ?덉퐫?? {features.section_record_counts.get('?됰룞?뱀꽦 諛?醫낇빀?섍껄', 0)}",
            ],
        )
    )
    
    axes.append(
        _authenticity_risk_axis(
            score=authenticity_risk,
            hints=[
                f"?뚯떛 ?좊ː?? {round(features.reliability_score, 3)}",
                f"needs_review 臾몄꽌 ?? {features.needs_review_documents}",
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
        rationale = "洹쇨굅 ?鍮?怨쇱옣 ?꾪뿕????퀬 湲곕줉 ?쇨??깆씠 ?좎??⑸땲??"
    elif score <= 60:
        band = "watch"
        severity = "medium"
        rationale = "?쇰? 援ш컙?먯꽌 洹쇨굅 諛?꾩? ?ㅻ챸 ?쇨??깆쓣 異붽? ?뺤씤?댁빞 ?⑸땲??"
    else:
        band = "high_risk"
        severity = "high"
        rationale = "洹쇨굅 ?鍮?二쇱옣 怨쇱옣 媛?μ꽦???덉뼱 蹂댁닔???쒖닠怨?利앷굅 蹂닿컯???꾩슂?⑸땲??"
    return AdmissionAxisResult(
        key="authenticity_risk",
        label="吏꾩젙?굿룰낵???꾪뿕",
        score=score,
        band=band,
        severity=severity,
        rationale=rationale,
        evidence_hints=hints,
    )


def _major_alignment_rationale(score: int) -> str:
    if score >= 80:
        return "?꾧났 ?곌퀎 ?ㅼ썙?쒖? 怨쇰ぉ 遺꾪룷媛 鍮꾧탳???덉젙?곸쑝濡??곌껐?⑸땲??"
    if score >= 60:
        return "?꾧났 ?곌퀎 ?⑥꽌???덉쑝??湲곕줉 ?꾨컲?먯꽌 諛섎났 ?몄텧?????꾩슂?⑸땲??"
    return "?꾧났 ?곌껐 ?좏샇媛 ?쏀빐 ?듭떖 怨쇰ぉ/?쒕룞 洹쇨굅瑜?紐낆떆?곸쑝濡?蹂닿컯?댁빞 ?⑸땲??"


def _inquiry_rationale(score: int) -> str:
    if score >= 80:
        return "?먭뎄 ?먮쫫???⑤컻?깆씠 ?꾨땲???꾩냽 ?쒕룞?쇰줈 ?댁뼱吏???⑦꽩???뺤씤?⑸땲??"
    if score >= 60:
        return "?먭뎄 ?곗냽???⑥꽌媛 ?쇰? ?덉쑝??怨쇰ぉ/二쇱젣 ?щ벑???먮쫫????紐낇솗???댁빞 ?⑸땲??"
    return "?쒕룞???⑦렪?곸쑝濡?蹂댁씪 ???덉뼱 鍮꾧탳쨌?꾩냽쨌?ы솕 ?먮쫫???섎룄?곸쑝濡??곌껐?댁빞 ?⑸땲??"


def _evidence_rationale(score: int) -> str:
    if score >= 80:
        return "?섏튂/愿李?湲곕줉 洹쇨굅媛 異⑸텇??二쇱옣??諛⑹뼱?섍린 醫뗭뒿?덈떎."
    if score >= 60:
        return "?듭떖 洹쇨굅???덉쑝??二쇱옣 ?鍮?利앷굅 諛?꾨? ???④퀎 ???믪씪 ?꾩슂媛 ?덉뒿?덈떎."
    return "洹쇨굅 諛?꾧? ??븘 寃곌낵 二쇱옣蹂대떎 愿李??ъ떎??癒쇱? 異뺤쟻?섎뒗 寃껋씠 ?덉쟾?⑸땲??"


def _process_rationale(score: int) -> str:
    if score >= 80:
        return "怨쇱젙 ?ㅻ챸怨?諛섏꽦 湲곕줉??鍮꾧탳??援ъ껜?곸쑝濡??쒕윭?⑸땲??"
    if score >= 60:
        return "怨쇱젙 ?쒖닠? ?덉쑝??諛⑸쾿-?쒓퀎-媛쒖꽑???곌껐?????먮졆?섍쾶 ?곸뼱???⑸땲??"
    return "臾댁뾿???덈뒗吏??蹂댁씠吏留???洹몃젃寃??덈뒗吏? ?쒓퀎 ?ㅻ챸??遺議깊빀?덈떎."


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
    if features.section_presence.get("援먭낵?숈뒿諛쒕떖?곹솴") and features.section_record_counts.get("援먭낵?숈뒿諛쒕떖?곹솴", 0) >= 3:
        strengths.append("援먭낵?숈뒿諛쒕떖?곹솴 湲곕줉?됱씠 異⑸텇???숈뾽 洹쇨굅 ?쒖떆???좊━?⑸땲??")
    if not strengths:
        strengths.append("?듭떖 ?뱀뀡??湲곕컲?쇰줈 ?뺤옣 媛?ν븳 理쒖냼 洹쇨굅???뺣낫?섏뼱 ?덉뒿?덈떎.")
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
            gaps.append(f"{section_key} ?뱀뀡 洹쇨굅媛 遺議깊빀?덈떎.")
    if not gaps:
        gaps.append("?꾩옱 援ъ“瑜??좎??섎㈃???몃? 利앷굅(?섏튂, 鍮꾧탳, 諛섏꽦)瑜?異붽??섎㈃ ?꾩꽦?꾧? ?믪븘吏묐땲??")
    return _dedupe_keep_order(gaps)[:10]


def _build_risk_flags(
    *,
    features: StudentRecordFeatures,
    admission_axes: list[AdmissionAxisResult],
) -> list[str]:
    flags = list(features.risk_flags)
    authenticity = next((axis for axis in admission_axes if axis.key == "authenticity_risk"), None)
    if authenticity and authenticity.band == "high_risk":
        flags.append("吏꾩젙?굿룰낵???꾪뿕 異뺤씠 ?믪븘 ?쒗쁽 ?섏쐞瑜?蹂댁닔?곸쑝濡??좎??댁빞 ?⑸땲??")
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
            actions.append("?꾩옱 湲곕줉 以??꾧났 愿??怨쇰ぉ/?쒕룞 臾몄옣????臾몃떒?쇰줈 ?ъ젙?ы빐 ?곌껐?깆쓣 紐낆떆?섏꽭??")
        elif axis.key == "inquiry_continuity":
            actions.append("媛숈? 二쇱젣瑜?2???댁긽 ?댁뼱吏???먮쫫(臾몄젣-?쒕룄-媛쒖꽑)?쇰줈 ?뺣━?섏꽭??")
        elif axis.key == "evidence_density":
            actions.append("二쇱옣留덈떎 愿李?洹쇨굅 1媛??댁긽???곌껐?섍퀬 ?섏튂/?ъ떎 ?쒗쁽???곗꽑 諛곗튂?섏꽭??")
        elif axis.key == "process_explanation":
            actions.append("諛⑸쾿-?쒓퀎-媛쒖꽑 ?쒖꽌濡?怨쇱젙 ?ㅻ챸??3臾몄옣 ?댁긽 怨좎젙 ?쒗뵆由우쑝濡??묒꽦?섏꽭??")

    if features.needs_review:
        actions.append("needs_review ?쒖떆 臾몄꽌???먮Ц ?議????듭떖 臾몄옣??蹂댁닔?곸쑝濡??ъ옉?깊븯?몄슂.")
    if target_major:
        actions.append(f"{target_major} 吏??留λ씫??留욌뒗 ?쒕룞 1媛쒕? ?좎젙??洹쇨굅 以묒떖?쇰줈 ?ы솕 湲곕줉??異붽??섏꽭??")
    return _dedupe_keep_order(actions)[:8]


def _build_recommended_topics(
    *,
    features: StudentRecordFeatures,
    target_major: str | None,
) -> list[str]:
    topics = [subject for subject, _ in features.subject_distribution.items()][:5]
    if target_major:
        topics.insert(0, f"{target_major} ?곌퀎 ?ы솕?먭뎄")
    if not topics:
        topics = ["援먭낵 湲곕컲 ?ы솕?먭뎄", "吏꾨줈 ?곌퀎 ?꾨줈?앺듃", "鍮꾧탳쨌遺꾩꽍???쒕룞"]
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

