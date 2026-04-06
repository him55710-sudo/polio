from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from polio_api.db.models.inquiry import Inquiry
from polio_api.schemas.inquiry import InquiryCreate
from polio_api.services.prompt_registry import PromptRegistryError, get_prompt_registry
from polio_api.core.config import get_settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

TRIAGE_PROMPT_NAME = "inquiry-support.contact-triage"
_FABRICATION_PATTERN = re.compile(r"\b(make up|fabricat(?:e|ed|ion)|조작|거짓|허위)\b", re.IGNORECASE)
_GUARANTEE_PATTERN = re.compile(r"\b(guarantee|guaranteed|100%|합격 보장|확정 합격)\b", re.IGNORECASE)
_SENSITIVE_PATTERN = re.compile(
    r"(\b\d{6}\s*[-]?\s*[1-4]\d{6}\b|\b01[016789][- ]?\d{3,4}[- ]?\d{4}\b)",
    re.IGNORECASE,
)


def create_inquiry(db: Session, payload: InquiryCreate) -> Inquiry:
    inquiry = Inquiry(
        inquiry_type=payload.inquiry_type,
        status="received",
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        subject=payload.subject,
        message=payload.message,
        inquiry_category=payload.inquiry_category,
        institution_name=payload.institution_name,
        institution_type=payload.institution_type,
        source_path=payload.source_path,
        extra_fields=_build_extra_fields(payload),
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    
    # Notify via email asynchronously so it doesn't block the API response
    threading.Thread(target=_send_email_notification_safe, args=(payload,), daemon=True).start()
    
    return inquiry

def _send_email_notification_safe(payload: InquiryCreate) -> None:
    try:
        settings = get_settings()
        if not settings.smtp_enabled or not settings.smtp_username or not settings.smtp_password:
            return
            
        msg = MIMEMultipart()
        msg["From"] = settings.smtp_username
        msg["To"] = settings.smtp_receiver_email
        msg["Subject"] = f"[{payload.inquiry_type.upper()}] 새 문의가 접수되었습니다: {payload.name}"
        
        body = f"""유형: {payload.inquiry_type}
카테고리: {payload.inquiry_category or '-'}
이름: {payload.name or '-'}
이메일: {payload.email}
연락처: {payload.phone or '-'}
기관명: {payload.institution_name or '-'}
발생위치: {payload.context_location or '-'}

--- 문의내용 ---
{payload.message}
"""
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Failed to send email notification: {e}")



def _build_extra_fields(payload: InquiryCreate) -> dict[str, Any]:
    extra_fields: dict[str, Any] = {}
    if payload.metadata:
        extra_fields["metadata"] = payload.metadata
    if payload.context_location:
        extra_fields["context_location"] = payload.context_location
    extra_fields["triage"] = _build_inquiry_triage(payload)
    return extra_fields


def _build_inquiry_triage(payload: InquiryCreate) -> dict[str, Any]:
    risk_flags = _detect_risk_flags(payload)
    category = payload.inquiry_category or _derive_category(payload)
    priority = _resolve_priority(payload=payload, risk_flags=risk_flags)

    prompt_meta: dict[str, str] = {"name": TRIAGE_PROMPT_NAME, "version": "unknown"}
    try:
        asset = get_prompt_registry().get_asset(TRIAGE_PROMPT_NAME)
        prompt_meta = {"name": asset.meta.name, "version": asset.meta.version}
    except PromptRegistryError:
        pass

    return {
        "prompt_asset": prompt_meta,
        "triage_method": "deterministic_v1",
        "category": category,
        "priority": priority,
        "internal_summary": _build_internal_summary(payload=payload, category=category, risk_flags=risk_flags),
        "follow_up_questions": _build_follow_up_questions(payload),
        "risk_flags": risk_flags,
    }


def _derive_category(payload: InquiryCreate) -> str:
    if payload.inquiry_type == "partnership":
        return "partnership_request"
    if payload.inquiry_type == "bug_report":
        return "bug"
    return "other"


def _resolve_priority(*, payload: InquiryCreate, risk_flags: list[str]) -> str:
    if risk_flags:
        return "high"
    if payload.inquiry_type == "bug_report":
        return "high"
    if payload.inquiry_type == "partnership":
        return "medium"
    if payload.inquiry_category == "account_login":
        return "medium"
    return "low"


def _build_internal_summary(*, payload: InquiryCreate, category: str, risk_flags: list[str]) -> str:
    if payload.inquiry_type == "partnership":
        institution_type = payload.institution_type or "organization"
        return (
            f"{payload.institution_name} ({institution_type}) submitted a partnership inquiry "
            f"through {payload.name}. Review scope, deployment context, and follow-up channel."
        )
    if payload.inquiry_type == "bug_report":
        location = payload.context_location or payload.source_path or "unknown location"
        return (
            f"{payload.name} reported a {category} issue around {location}. "
            f"Review reproducibility details and any user-blocking impact."
        )

    subject = payload.subject or category
    summary = f"{payload.name or 'User'} submitted a {category} inquiry about {subject}."
    if risk_flags:
        summary += " The message contains policy-sensitive language and should be reviewed carefully."
    return summary


def _build_follow_up_questions(payload: InquiryCreate) -> list[str]:
    questions: list[str] = []
    if payload.inquiry_type == "partnership":
        questions.append("What student group, program size, or rollout scope is being considered?")
        questions.append("What outcome is the institution hoping to evaluate first?")
    elif payload.inquiry_type == "bug_report":
        questions.append("What exact steps reproduce the issue?")
        questions.append("Which device, browser, or app environment was involved?")
    else:
        questions.append("What exact step or workflow is currently blocked?")
        questions.append("What result were they expecting instead?")
    return questions


def _detect_risk_flags(payload: InquiryCreate) -> list[str]:
    text = " ".join(
        value
        for value in [
            payload.subject or "",
            payload.message,
            payload.context_location or "",
            payload.source_path or "",
        ]
        if value
    )
    risk_flags: list[str] = []
    if _FABRICATION_PATTERN.search(text):
        risk_flags.append("fabrication_request")
    if _GUARANTEE_PATTERN.search(text):
        risk_flags.append("guaranteed_outcome_request")
    if _SENSITIVE_PATTERN.search(payload.message):
        risk_flags.append("sensitive_data_in_message")
    return risk_flags
