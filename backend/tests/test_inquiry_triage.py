from __future__ import annotations

from unifoli_api.schemas.inquiry import InquiryCreate
from unifoli_api.services.inquiry_service import _build_inquiry_triage


def test_bug_report_triage_marks_high_priority_and_follow_ups() -> None:
    payload = InquiryCreate(
        inquiry_type="bug_report",
        name="Tester",
        email="tester@example.com",
        message="로그???�면?�서 100% ?�격 보장 문구가 보이�??�류가 ?�니??",
        inquiry_category="bug",
        context_location="/login",
    )

    triage = _build_inquiry_triage(payload)

    assert triage["prompt_asset"]["name"] == "inquiry-support.contact-triage"
    assert triage["priority"] == "high"
    assert "guaranteed_outcome_request" in triage["risk_flags"]
    assert len(triage["follow_up_questions"]) >= 2

