import asyncio
from types import SimpleNamespace

from unifoli_api.services.async_job_service import (
    _is_non_retryable_failure,
    _public_failure_reason,
    _run_async_callable,
)
from unifoli_domain.enums import AsyncJobType


def test_diagnosis_public_failure_reason_surfaces_parse_hint() -> None:
    job = SimpleNamespace(job_type=AsyncJobType.DIAGNOSIS.value)

    reason = _public_failure_reason(
        job,
        "Parsed document content is empty. Re-run parsing with a clearer source file.",
    )

    assert "Re-run parsing" in reason
    assert "Diagnosis requires parsed text evidence" in reason


def test_diagnosis_public_failure_reason_surfaces_storage_saturation() -> None:
    job = SimpleNamespace(job_type=AsyncJobType.DIAGNOSIS.value)

    reason = _public_failure_reason(
        job,
        "OperationalError: (sqlite3.OperationalError) database or disk is full",
    )

    assert "temporarily saturated" in reason


def test_diagnosis_disk_full_is_non_retryable() -> None:
    job = SimpleNamespace(job_type=AsyncJobType.DIAGNOSIS.value)

    assert _is_non_retryable_failure(
        job,
        reason="(sqlite3.OperationalError) database or disk is full",
        internal_reason=None,
    )


def test_run_async_callable_works_inside_running_loop() -> None:
    async def _sample(value: int) -> int:
        await asyncio.sleep(0.01)
        return value + 1

    async def _invoke_from_running_loop() -> int:
        return _run_async_callable(_sample, 41)

    assert asyncio.run(_invoke_from_running_loop()) == 42

