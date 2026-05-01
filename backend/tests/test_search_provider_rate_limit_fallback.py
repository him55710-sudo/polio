from __future__ import annotations

import asyncio

from unifoli_api.services.live_web_search_service import LiveWebSearchUnavailable
from unifoli_api.services.scholar_service import ScholarPaper, ScholarSearchResult, ScholarServiceError
from unifoli_api.services.search_provider_service import search_research_sources


def test_search_provider_semantic_rate_limit_falls_back_to_kci(monkeypatch) -> None:
    async def fake_semantic(query: str, limit: int = 5) -> ScholarSearchResult:
        del query, limit
        raise ScholarServiceError(
            status_code=429,
            detail="Semantic Scholar rate limit exceeded. Please retry later.",
            retry_after=60,
        )

    async def fake_kci(query: str, limit: int = 5) -> ScholarSearchResult:
        del query, limit
        return ScholarSearchResult(
            query="biology",
            total=1,
            papers=[
                ScholarPaper(
                    title="KCI fallback paper",
                    authors=["KCI Author"],
                    year=2024,
                    citationCount=0,
                    url="https://example.org/kci",
                )
            ],
            source="kci",
            requested_source="kci",
        )

    monkeypatch.setattr("unifoli_api.services.search_provider_service.search_semantic_scholar_papers", fake_semantic)
    monkeypatch.setattr("unifoli_api.services.search_provider_service.search_kci_papers", fake_kci)

    result = asyncio.run(search_research_sources(query="biology", source="semantic", limit=5))

    assert result.requested_source == "semantic"
    assert result.source == "kci"
    assert result.fallback_applied is True
    assert result.providers_used == ["kci"]
    assert "Semantic Scholar" in (result.limitation_note or "")
    assert result.papers[0].title == "KCI fallback paper"


def test_search_provider_live_web_and_semantic_rate_limits_return_empty_result(monkeypatch) -> None:
    async def fake_live_web(query: str, limit: int = 5) -> ScholarSearchResult:
        del query, limit
        raise LiveWebSearchUnavailable("Live web provider is not configured.")

    async def fake_semantic(query: str, limit: int = 5) -> ScholarSearchResult:
        del query, limit
        raise ScholarServiceError(
            status_code=429,
            detail="Semantic Scholar rate limit exceeded. Please retry later.",
        )

    async def fake_kci(query: str, limit: int = 5) -> ScholarSearchResult:
        del query, limit
        raise ScholarServiceError(
            status_code=503,
            detail="KCI search is not configured for this environment.",
        )

    monkeypatch.setattr("unifoli_api.services.search_provider_service.search_live_web_papers", fake_live_web)
    monkeypatch.setattr("unifoli_api.services.search_provider_service.search_semantic_scholar_papers", fake_semantic)
    monkeypatch.setattr("unifoli_api.services.search_provider_service.search_kci_papers", fake_kci)

    result = asyncio.run(search_research_sources(query="biology", source="live_web", limit=5))

    assert result.requested_source == "live_web"
    assert result.source == "semantic"
    assert result.fallback_applied is True
    assert result.papers == []
    assert result.total == 0
    assert "conversation can continue" in (result.limitation_note or "")
