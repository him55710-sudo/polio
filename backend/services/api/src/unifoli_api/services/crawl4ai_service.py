import asyncio
import logging
from typing import Any

logger = logging.getLogger("unifoli.services.crawl4ai")

def is_crawl4ai_available() -> bool:
    """
    Check if Crawl4AI is installed and available.
    """
    try:
        from crawl4ai import AsyncWebCrawler
        return True
    except (ImportError, Exception):
        return False

async def crawl_with_crawl4ai(
    url: str, 
    *, 
    max_chars: int = 5000, 
    timeout_seconds: float = 12.0
) -> dict[str, Any]:
    """
    Crawl a URL using Crawl4AI if available.
    """
    if not is_crawl4ai_available():
        return {
            "url": url,
            "title": None,
            "text": None,
            "markdown": None,
            "provider": "crawl4ai",
            "status": "unavailable",
            "error": "Crawl4AI is not installed.",
            "char_count": 0
        }

    try:
        from crawl4ai import AsyncWebCrawler
        
        async with AsyncWebCrawler() as crawler:
            # version-specific API check might be needed, but assuming standard run for now
            try:
                result = await asyncio.wait_for(
                    crawler.arun(url=url), 
                    timeout=timeout_seconds
                )
                
                # Crawl4AI result structure typically has markdown and text
                # We truncate to max_chars to save tokens and avoid huge logs
                markdown_content = result.markdown or ""
                text_content = result.extracted_content or result.text or ""
                
                title = getattr(result, "title", None) or getattr(result, "metadata", {}).get("title")
                
                return {
                    "url": url,
                    "title": title,
                    "text": text_content[:max_chars],
                    "markdown": markdown_content[:max_chars],
                    "provider": "crawl4ai",
                    "status": "ok",
                    "error": None,
                    "char_count": len(text_content)
                }
            except asyncio.TimeoutError:
                return {
                    "url": url,
                    "title": None,
                    "text": None,
                    "markdown": None,
                    "provider": "crawl4ai",
                    "status": "error",
                    "error": f"Crawl timeout after {timeout_seconds}s",
                    "char_count": 0
                }
    except Exception as e:
        logger.error(f"Error crawling {url} with Crawl4AI: {str(e)}")
        return {
            "url": url,
            "title": None,
            "text": None,
            "markdown": None,
            "provider": "crawl4ai",
            "status": "error",
            "error": f"Internal crawl error: {str(e)[:100]}",
            "char_count": 0
        }
