from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlparse

from unifoli_api.services.live_web_search_service import (
    LiveWebSearchError,
    LiveWebSearchUnavailable,
    search_live_web_papers,
)
from unifoli_api.services.scholar_service import (
    ScholarPaper,
    ScholarSearchResult,
    ScholarServiceError,
    search_kci_papers,
    search_semantic_scholar_papers,
)

SearchSource = Literal["semantic", "kci", "live_web", "both"]
GroundingSourceType = Literal[
    "uploaded_student_record",
    "academic_source",
    "official_guideline",
    "live_web_source",
]

_ALLOWED_SOURCES: set[str] = {"semantic", "kci", "live_web", "both"}
_GROUNDING_SOURCE_TYPES: set[str] = {
    "uploaded_student_record",
    "academic_source",
    "official_guideline",
    "live_web_source",
}
_OFFICIAL_DOMAIN_HINTS: tuple[str, ...] = (
    ".go.kr",
    ".ac.kr",
    ".edu",
    ".ed.kr",
    "kice.re.kr",
    "moe.go.kr",
    "keris.or.kr",
)
_RECOVERABLE_SCHOLAR_STATUS_CODES = {429, 502, 503, 504}


@dataclass(slots=True)
class SearchProviderResolution:
    source: SearchSource
    providers_used: list[str]
    fallback_applied: bool = False
    limitation_note: str | None = None


def normalize_search_source(source: str | None) -> SearchSource:
    normalized = (source or "semantic").strip().lower()
    if normalized not in _ALLOWED_SOURCES:
        raise ScholarServiceError(
            status_code=422,
            detail="Invalid research source. Use semantic, kci, live_web, or both.",
        )
    return normalized  # type: ignore[return-value]


def source_type_label(source_type: GroundingSourceType) -> str:
    if source_type == "uploaded_student_record":
        return "Uploaded Student Record"
    if source_type == "academic_source":
        return "Academic Source"
    if source_type == "official_guideline":
        return "Official Guideline"
    return "Live Web Source"


def normalize_grounding_source_type(
    source_type: str | None,
    *,
    fallback: GroundingSourceType = "uploaded_student_record",
) -> GroundingSourceType:
    normalized = (source_type or "").strip().lower()
    if normalized in _GROUNDING_SOURCE_TYPES:
        return normalized  # type: ignore[return-value]

    if normalized in {
        "student_record",
        "student",
        "manual",
        "manual_note",
        "note",
        "user_note",
        "draft",
        "project_doc",
    }:
        return "uploaded_student_record"

    if normalized in {
        "academic",
        "paper",
        "scholar",
        "semantic",
        "kci",
        "scholar_semantic",
        "scholar_kci",
        "scholar_both",
    }:
        return "academic_source"

    if normalized in {
        "official",
        "official_source",
        "guideline",
        "policy",
        "gov",
        "ministry",
    }:
        return "official_guideline"

    if normalized in {
        "web",
        "live_web",
        "liveweb",
        "news",
        "community",
        "blog",
        "scholar_live_web",
    }:
        return "live_web_source"

    return fallback


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_provider_name(source: SearchSource) -> str:
    if source == "semantic":
        return "semantic_scholar"
    if source == "kci":
        return "kci"
    if source == "live_web":
        return "live_web"
    return "hybrid_academic"


def _normalize_domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = (urlparse(url).hostname or "").strip().lower()
    except Exception:  # noqa: BLE001
        return None
    return host or None


def _is_official_domain(domain: str | None) -> bool:
    if not domain:
        return False
    return any(domain.endswith(hint) or hint in domain for hint in _OFFICIAL_DOMAIN_HINTS)


def _freshness_label_from_year(year: int | None) -> str:
    if year is None:
        return "Year Unknown"
    current_year = datetime.now(timezone.utc).year
    if year >= current_year - 1:
        return "Latest"
    if year >= current_year - 3:
        return "Recent"
    return "Older Record"


def _resolve_source_type(*, resolved_source: SearchSource, domain: str | None) -> GroundingSourceType:
    if resolved_source in {"semantic", "kci", "both"}:
        return "academic_source"
    if _is_official_domain(domain):
        return "official_guideline"
    return "live_web_source"


def _annotate_paper(
    paper: ScholarPaper,
    *,
    resolved_source: SearchSource,
    requested_source: SearchSource,
    source_provider: str,
    retrieved_at: str,
) -> ScholarPaper:
    domain = _normalize_domain(paper.url)
    source_type = _resolve_source_type(resolved_source=resolved_source, domain=domain)
    source_label = source_type_label(source_type)
    return paper.model_copy(
        update={
            "source_type": source_type,
            "source_provider": source_provider,
            "source_label": source_label,
            "source_domain": domain,
            "freshness_label": _freshness_label_from_year(paper.year),
            "retrieved_at": retrieved_at,
            "requested_source": requested_source,
        }
    )


def _annotate_result(
    result: ScholarSearchResult,
    *,
    requested_source: SearchSource,
    resolved: SearchProviderResolution,
) -> ScholarSearchResult:
    retrieved_at = _utc_now_iso()
    provider_label = resolved.providers_used[0] if resolved.providers_used else _resolve_provider_name(resolved.source)
    annotated_papers = [
        _annotate_paper(
            paper,
            resolved_source=resolved.source,
            requested_source=requested_source,
            source_provider=provider_label,
            retrieved_at=retrieved_at,
        )
        for paper in result.papers
    ]
    source_type_counts = dict(
        Counter(
            normalize_grounding_source_type(
                paper.source_type,
                fallback="academic_source" if resolved.source in {"semantic", "kci", "both"} else "live_web_source",
            )
            for paper in annotated_papers
        )
    )
    return result.model_copy(
        update={
            "papers": annotated_papers,
            "requested_source": requested_source,
            "source": resolved.source,
            "fallback_applied": resolved.fallback_applied,
            "limitation_note": resolved.limitation_note,
            "providers_used": resolved.providers_used,
            "retrieved_at": retrieved_at,
            "source_type_counts": source_type_counts,
        }
    )


def _dedupe_and_cap(papers: list[ScholarPaper], *, limit: int) -> list[ScholarPaper]:
    seen: set[str] = set()
    unique: list[ScholarPaper] = []
    for paper in papers:
        title = (paper.title or "").strip().lower()
        if not title or title in seen:
            continue
        seen.add(title)
        unique.append(paper)
        if len(unique) >= limit:
            break
    return unique


def _is_recoverable_scholar_error(exc: ScholarServiceError) -> bool:
    return exc.status_code in _RECOVERABLE_SCHOLAR_STATUS_CODES


def _provider_error_note(provider: str, exc: ScholarServiceError) -> str:
    note = f"{provider}: {exc.detail}"
    if exc.retry_after:
        note = f"{note} Retry after {exc.retry_after} seconds."
    return note


def _join_limitation_notes(*notes: str | None) -> str | None:
    cleaned = [note.strip() for note in notes if note and note.strip()]
    if not cleaned:
        return None
    return " ".join(cleaned)[:500]


def _empty_fallback_result(
    *,
    query: str,
    requested_source: SearchSource,
    resolved_source: SearchSource,
    providers_used: list[str],
    limitation_note: str | None,
) -> ScholarSearchResult:
    return ScholarSearchResult(
        query=query.strip(),
        total=0,
        papers=[],
        source=resolved_source,
        requested_source=requested_source,
        fallback_applied=True,
        limitation_note=limitation_note,
        providers_used=providers_used,
        retrieved_at=None,
        source_type_counts={},
    )


async def _semantic_fallback_to_kci_or_empty(
    *,
    query: str,
    limit: int,
    requested_source: SearchSource,
    semantic_error: ScholarServiceError,
    prefix_note: str | None = None,
) -> ScholarSearchResult:
    semantic_note = _provider_error_note("Semantic Scholar", semantic_error)
    try:
        kci = await search_kci_papers(query=query, limit=limit)
    except ScholarServiceError as kci_error:
        if not _is_recoverable_scholar_error(kci_error):
            raise
        limitation_note = _join_limitation_notes(
            prefix_note,
            semantic_note,
            _provider_error_note("KCI fallback unavailable", kci_error),
            "Returned no external paper results so the conversation can continue.",
        )
        empty = _empty_fallback_result(
            query=query,
            requested_source=requested_source,
            resolved_source="semantic",
            providers_used=["semantic_scholar"],
            limitation_note=limitation_note,
        )
        return _annotate_result(
            empty,
            requested_source=requested_source,
            resolved=SearchProviderResolution(
                source="semantic",
                providers_used=["semantic_scholar"],
                fallback_applied=True,
                limitation_note=limitation_note,
            ),
        )

    limitation_note = _join_limitation_notes(
        prefix_note,
        semantic_note,
        "KCI fallback results were returned.",
    )
    enriched = kci.model_copy(
        update={
            "fallback_applied": True,
            "limitation_note": limitation_note,
        }
    )
    return _annotate_result(
        enriched,
        requested_source=requested_source,
        resolved=SearchProviderResolution(
            source="kci",
            providers_used=["kci"],
            fallback_applied=True,
            limitation_note=limitation_note,
        ),
    )


async def search_research_sources(
    *,
    query: str,
    limit: int = 5,
    source: str | None = None,
) -> ScholarSearchResult:
    requested_source = normalize_search_source(source)

    if requested_source == "semantic":
        try:
            result = await search_semantic_scholar_papers(query=query, limit=limit)
        except ScholarServiceError as exc:
            if not _is_recoverable_scholar_error(exc):
                raise
            return await _semantic_fallback_to_kci_or_empty(
                query=query,
                limit=limit,
                requested_source=requested_source,
                semantic_error=exc,
            )
        return _annotate_result(
            result,
            requested_source=requested_source,
            resolved=SearchProviderResolution(source="semantic", providers_used=["semantic_scholar"]),
        )

    if requested_source == "kci":
        result = await search_kci_papers(query=query, limit=limit)
        return _annotate_result(
            result,
            requested_source=requested_source,
            resolved=SearchProviderResolution(source="kci", providers_used=["kci"]),
        )

    if requested_source == "both":
        papers: list[ScholarPaper] = []
        providers_used: list[str] = []
        limitation_notes: list[str] = []

        try:
            semantic = await search_semantic_scholar_papers(query=query, limit=limit)
            papers.extend(semantic.papers)
            providers_used.append("semantic_scholar")
        except ScholarServiceError as exc:
            if not _is_recoverable_scholar_error(exc):
                raise
            limitation_notes.append(_provider_error_note("Semantic Scholar", exc))

        try:
            kci = await search_kci_papers(query=query, limit=limit)
            papers.extend(kci.papers)
            providers_used.append("kci")
        except ScholarServiceError as exc:
            if not _is_recoverable_scholar_error(exc) or (not providers_used and not limitation_notes):
                raise
            limitation_notes.append(_provider_error_note("KCI", exc))

        limitation_note = _join_limitation_notes(*limitation_notes)
        if not providers_used and limitation_note:
            empty = _empty_fallback_result(
                query=query,
                requested_source=requested_source,
                resolved_source="both",
                providers_used=["semantic_scholar", "kci"],
                limitation_note=_join_limitation_notes(
                    limitation_note,
                    "Returned no external paper results so the conversation can continue.",
                ),
            )
            return _annotate_result(
                empty,
                requested_source=requested_source,
                resolved=SearchProviderResolution(
                    source="both",
                    providers_used=["semantic_scholar", "kci"],
                    fallback_applied=True,
                    limitation_note=empty.limitation_note,
                ),
            )

        merged = ScholarSearchResult(
            query=query.strip(),
            total=0,
            papers=_dedupe_and_cap(papers, limit=limit),
            source="both",
            requested_source="both",
            fallback_applied=bool(limitation_note),
            limitation_note=limitation_note,
            providers_used=providers_used or ["semantic_scholar", "kci"],
            retrieved_at=None,
            source_type_counts={},
        )
        merged.total = len(merged.papers)
        return _annotate_result(
            merged,
            requested_source=requested_source,
            resolved=SearchProviderResolution(
                source="both",
                providers_used=providers_used or ["semantic_scholar", "kci"],
                fallback_applied=bool(limitation_note),
                limitation_note=limitation_note,
            ),
        )

    try:
        live_web = await search_live_web_papers(query=query, limit=limit)
        providers_used = live_web.providers_used or ["live_web"]
        return _annotate_result(
            live_web,
            requested_source=requested_source,
            resolved=SearchProviderResolution(source="live_web", providers_used=providers_used),
        )
    except (LiveWebSearchUnavailable, LiveWebSearchError) as live_exc:
        limitation = live_exc.reason
        if isinstance(live_exc, LiveWebSearchError) and live_exc.retry_after:
            limitation = f"{limitation} Retry after {live_exc.retry_after} seconds."
        try:
            fallback = await search_semantic_scholar_papers(query=query, limit=limit)
        except ScholarServiceError as semantic_exc:
            if not _is_recoverable_scholar_error(semantic_exc):
                raise
            return await _semantic_fallback_to_kci_or_empty(
                query=query,
                limit=limit,
                requested_source=requested_source,
                semantic_error=semantic_exc,
                prefix_note=limitation,
            )
        fallback_enriched = fallback.model_copy(
            update={
                "requested_source": "live_web",
                "fallback_applied": True,
                "limitation_note": f"{limitation} Semantic Scholar fallback results were returned."[:500],
            }
        )
        return _annotate_result(
            fallback_enriched,
            requested_source=requested_source,
            resolved=SearchProviderResolution(
                source="semantic",
                providers_used=["semantic_scholar"],
                fallback_applied=True,
                limitation_note=fallback_enriched.limitation_note,
            ),
        )
