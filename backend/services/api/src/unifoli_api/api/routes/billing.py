from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from unifoli_api.api.deps import get_current_user, get_db
from unifoli_api.core.config import get_settings
from unifoli_api.core.rate_limit import rate_limit
from unifoli_api.db.models.payment_order import PaymentOrder
from unifoli_api.db.models.user import User

router = APIRouter()


@dataclass(frozen=True)
class PlanMeta:
    code: Literal["plus", "pro"]
    display_name: str
    amount: int


class TossCheckoutSessionRequest(BaseModel):
    plan_code: Literal["plus", "pro"]


class TossCheckoutSessionResponse(BaseModel):
    provider: Literal["toss"]
    plan_code: Literal["plus", "pro"]
    amount: int
    order_id: str
    order_name: str
    customer_name: str | None
    customer_email: str | None
    client_key: str
    success_url: str
    fail_url: str


class TossPaymentConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    payment_key: str = Field(min_length=1, max_length=200)
    order_id: str = Field(min_length=1, max_length=128)
    amount: int = Field(gt=0)


class TossPaymentConfirmResponse(BaseModel):
    provider: Literal["toss"]
    status: Literal["paid"]
    plan_code: Literal["plus", "pro"]
    amount: int
    order_id: str
    payment_key: str
    method: str | None
    approved_at: datetime | None


@router.post(
    "/toss/checkout-session",
    response_model=TossCheckoutSessionResponse,
    dependencies=[Depends(rate_limit(bucket="billing_checkout", limit=20, window_seconds=300))],
)
def create_toss_checkout_session(
    payload: TossCheckoutSessionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TossCheckoutSessionResponse:
    settings = get_settings()
    _ensure_toss_enabled(settings)
    plan_meta = _resolve_plan(payload.plan_code, settings)
    success_url, fail_url = _resolve_callback_urls(settings)
    order_id = f"unifoli-{secrets.token_hex(12)}"

    order = PaymentOrder(
        user_id=current_user.id,
        provider="toss",
        plan_code=plan_meta.code,
        order_id=order_id,
        order_name=f"Uni Folia {plan_meta.display_name}",
        amount=plan_meta.amount,
        status="ready",
        checkout_request={
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
    )
    db.add(order)
    db.commit()

    return TossCheckoutSessionResponse(
        provider="toss",
        plan_code=plan_meta.code,
        amount=plan_meta.amount,
        order_id=order_id,
        order_name=order.order_name,
        customer_name=current_user.name,
        customer_email=current_user.email,
        client_key=settings.toss_payments_client_key or "",
        success_url=success_url,
        fail_url=fail_url,
    )


@router.post(
    "/toss/confirm",
    response_model=TossPaymentConfirmResponse,
    dependencies=[Depends(rate_limit(bucket="billing_confirm", limit=30, window_seconds=300))],
)
async def confirm_toss_payment(
    payload: TossPaymentConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TossPaymentConfirmResponse:
    settings = get_settings()
    _ensure_toss_enabled(settings)

    order = (
        db.query(PaymentOrder)
        .filter(
            PaymentOrder.order_id == payload.order_id,
            PaymentOrder.user_id == current_user.id,
            PaymentOrder.provider == "toss",
        )
        .first()
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment order not found.")
    if order.amount != payload.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment amount mismatch.")
    if order.status == "paid":
        return TossPaymentConfirmResponse(
            provider="toss",
            status="paid",
            plan_code=order.plan_code,  # type: ignore[arg-type]
            amount=order.amount,
            order_id=order.order_id,
            payment_key=order.payment_key or payload.payment_key,
            method=order.method,
            approved_at=order.approved_at,
        )

    auth_token = base64.b64encode(f"{settings.toss_payments_secret_key}:".encode("utf-8")).decode("utf-8")
    request_payload = {
        "paymentKey": payload.payment_key,
        "orderId": payload.order_id,
        "amount": payload.amount,
    }

    timeout = httpx.Timeout(12.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            "https://api.tosspayments.com/v1/payments/confirm",
            json=request_payload,
            headers={
                "Authorization": f"Basic {auth_token}",
                "Content-Type": "application/json",
            },
        )

    response_json = _safe_json(response)
    if response.status_code // 100 != 2:
        order.status = "failed"
        order.failure_code = str(response_json.get("code") or response.status_code)
        order.failure_message = str(response_json.get("message") or "Payment confirmation failed.")
        order.confirm_response = response_json
        db.add(order)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Toss payment confirmation failed: {order.failure_message}",
        )

    approved_at = _parse_iso_datetime(response_json.get("approvedAt"))
    order.status = "paid"
    order.payment_key = payload.payment_key
    order.method = str(response_json.get("method") or "").strip() or None
    order.approved_at = approved_at
    order.failure_code = None
    order.failure_message = None
    order.confirm_response = response_json
    db.add(order)
    db.commit()

    return TossPaymentConfirmResponse(
        provider="toss",
        status="paid",
        plan_code=order.plan_code,  # type: ignore[arg-type]
        amount=order.amount,
        order_id=order.order_id,
        payment_key=order.payment_key or payload.payment_key,
        method=order.method,
        approved_at=order.approved_at,
    )


def _ensure_toss_enabled(settings) -> None:
    if not settings.toss_payments_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Toss payments are disabled.",
        )
    if not settings.toss_payments_client_key or not settings.toss_payments_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Toss payments are not configured.",
        )


def _resolve_plan(plan_code: Literal["plus", "pro"], settings) -> PlanMeta:
    if plan_code == "plus":
        return PlanMeta(code="plus", display_name="Plus", amount=settings.toss_plan_plus_amount)
    return PlanMeta(code="pro", display_name="Pro", amount=settings.toss_plan_pro_amount)


def _resolve_callback_urls(settings) -> tuple[str, str]:
    base_url = settings.toss_payments_frontend_base_url.rstrip("/")
    return f"{base_url}/payment/success", f"{base_url}/payment/fail"


def _safe_json(response: httpx.Response) -> dict:
    try:
        raw = response.json()
    except ValueError:
        return {"message": response.text}
    if isinstance(raw, dict):
        return raw
    return {"raw": raw}


def _parse_iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None
