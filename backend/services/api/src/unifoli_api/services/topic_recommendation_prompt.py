from __future__ import annotations

import json
from typing import Any

from unifoli_api.services.research_topic_scoring import TOPIC_SCORE_AXES
from unifoli_api.services.student_record_analyzer import analyze_student_record_summary


def build_topic_recommendation_prompt(
    *,
    subject: str,
    compact_payload: dict[str, Any],
    reference_text: str,
    starred_keywords: list[str],
    seed_count: int,
) -> str:
    target_major = str((compact_payload.get("target") or {}).get("major") or "")
    record_summary = str(compact_payload.get("record_flow_summary") or "")
    record_analysis = analyze_student_record_summary(record_summary, target_major=target_major)

    rubric = "\n".join(
        [
            "- connection: prior student-record connection, without copying original wording",
            "- depth: advances prior activities instead of repeating them",
            "- career_fit: logically tied to the intended major/career",
            "- creativity: fresh angle or interdisciplinary synthesis",
            "- feasibility: possible experiment, survey, simulation, build, or data analysis",
            "- social_meaning: connected to real issues such as climate, city, energy, aging, safety, environment, AI",
            "- admissions_appeal: shows problem awareness, major fit, inquiry ability, agency, growth potential",
            "- completion: data collection and conclusion are realistically possible",
            "- differentiation: not a generic topic many students would submit",
        ]
    )

    return (
        f"[Subject]\n{subject}\n\n"
        "[Student-derived context only]\n"
        f"{json.dumps(compact_payload, ensure_ascii=False)}\n\n"
        "[Derived signals; do not quote the original record]\n"
        f"- keywords: {', '.join(record_analysis.keywords[:12]) or 'none'}\n"
        f"- capabilities: {', '.join(record_analysis.capability_signals) or 'unknown'}\n"
        f"- major signals: {', '.join(record_analysis.major_signals) or 'unknown'}\n"
        f"- likely gaps: {', '.join(record_analysis.gap_signals) or 'none'}\n\n"
        "[Reference library candidates]\n"
        f"{reference_text or '- no reference candidates'}\n\n"
        "[Scoring rubric]\n"
        f"{rubric}\n"
        f"Use these score keys exactly: {', '.join(TOPIC_SCORE_AXES)}. Each score is 1-5.\n\n"
        "[Generation rules]\n"
        "- Recommend at least 5 strong topics. If possible, return the requested seed count.\n"
        "- Mix safe topics and challenging topics.\n"
        "- Penalize broad/common topics unless they include a concrete method and measurable variables.\n"
        "- Exclude topics with forced major fit or no feasible verification method.\n"
        "- If the user shows interest in architecture, city, environment, energy, structure, materials, or AI, prioritize those links.\n"
        "- Never copy the student-record wording. Analyze, reorganize, deepen, and extend it.\n\n"
        "[Each suggestion must include]\n"
        "title, one_line_summary, why_fit_student, link_to_record_flow, link_to_target_major_or_university, "
        "novelty_point, caution_note, record_connection_point, deepening_point, career_connection_point, "
        "social_issue_connection, experiment_or_survey_method, expected_output, outline_draft, "
        "admissions_strength, risk_or_supplement, scores, total_score, topic_band, suggestion_type.\n\n"
        "[Output]\n"
        "- Respond only as TopicSuggestionResponse JSON.\n"
        f"- Return up to {seed_count} suggestions. The server may expand them with library candidates.\n"
        f"- Starred keywords to respect: {', '.join(starred_keywords) or 'none'}.\n"
    )
