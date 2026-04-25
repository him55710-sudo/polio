import asyncio
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from unifoli_api.core.config import get_settings
from unifoli_api.services import crawl4ai_service

class CrawledPage(BaseModel):
    url: str
    title: str | None = None
    text: str | None = None
    markdown: str | None = None
    extracted_at: str
    provider: str = "none"
    status: Literal["ok", "error", "unavailable", "skipped"]
    error: str | None = None
    source_domain: str | None = None
    char_count: int = 0

async def crawl_url(
    url: str, 
    *, 
    max_chars: int | None = None, 
    timeout_seconds: float | None = None
) -> CrawledPage:
    """
    Crawl a single URL and return a CrawledPage.
    """
    settings = get_settings()
    
    # 1. Basic URL validation
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return CrawledPage(
            url=url,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            status="skipped",
            error="Invalid or non-http(s) URL",
            provider="none"
        )
    
    source_domain = parsed.hostname
    
    # 2. Check if Crawl4AI is enabled in settings
    if not settings.crawl4ai_enabled:
        return CrawledPage(
            url=url,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            status="unavailable",
            error="Crawl4AI is disabled in configuration.",
            provider="crawl4ai",
            source_domain=source_domain
        )
    
    # 3. Use Crawl4AI service
    limit_chars = max_chars or settings.research_crawl_max_chars_per_page
    limit_timeout = timeout_seconds or settings.research_crawl_timeout_seconds
    
    result = await crawl4ai_service.crawl_with_crawl4ai(
        url=url,
        max_chars=limit_chars,
        timeout_seconds=limit_timeout
    )
    
    return CrawledPage(
        url=url,
        title=result.get("title"),
        text=result.get("text"),
        markdown=result.get("markdown"),
        extracted_at=datetime.now(timezone.utc).isoformat(),
        provider=str(result.get("provider", "crawl4ai")),
        status=result.get("status", "error"),
        error=result.get("error"),
        source_domain=source_domain,
        char_count=result.get("char_count", 0)
    )

async def crawl_many(
    urls: list[str], 
    *, 
    max_pages: int | None = None, 
    max_chars_per_page: int | None = None
) -> list[CrawledPage]:
    """
    Crawl multiple URLs, limited by max_pages.
    """
    settings = get_settings()
    
    # Remove duplicates and limit pages
    unique_urls = list(dict.fromkeys(urls))
    limit = max_pages or settings.research_crawl_max_pages
    target_urls = unique_urls[:limit]
    
    if not target_urls:
        return []
    
    # Crawl URLs concurrently but safely
    tasks = [
        crawl_url(url, max_chars=max_chars_per_page) 
        for url in target_urls
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    final_pages = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            final_pages.append(CrawledPage(
                url=target_urls[i],
                extracted_at=datetime.now(timezone.utc).isoformat(),
                status="error",
                error=f"Task exception: {str(res)}",
                provider="crawl4ai"
            ))
        else:
            final_pages.append(res)
            
    return final_pages
