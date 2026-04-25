import type { CrawledPage } from '../types/crawl';

const CACHE_PREFIX = 'unifoli_crawl_cache_';
const DEFAULT_TTL = 7 * 24 * 60 * 60 * 1000; // 7 days

interface CacheEntry {
  page: CrawledPage;
  expiresAt: number;
}

export function buildUrlCrawlCacheKey(url: string): string {
  // Simple hash or b64 to make it a safe key
  return `${CACHE_PREFIX}${btoa(url).slice(0, 32)}`;
}

export function getCachedCrawledPage(url: string): CrawledPage | null {
  try {
    const key = buildUrlCrawlCacheKey(url);
    const item = localStorage.getItem(key);
    if (!item) return null;

    const entry: CacheEntry = JSON.parse(item);
    if (Date.now() > entry.expiresAt) {
      localStorage.removeItem(key);
      return null;
    }

    return entry.page;
  } catch (e) {
    console.error('Error reading from crawl cache:', e);
    return null;
  }
}

export function setCachedCrawledPage(
  url: string, 
  page: CrawledPage, 
  ttlMs: number = DEFAULT_TTL
): void {
  // Only cache successful or "permanently" unavailable results
  if (page.status !== 'ok' && page.status !== 'unavailable') return;

  try {
    const key = buildUrlCrawlCacheKey(url);
    const entry: CacheEntry = {
      page,
      expiresAt: Date.now() + ttlMs
    };
    localStorage.setItem(key, JSON.stringify(entry));
  } catch (e) {
    // LocalStorage might be full
    console.warn('Error writing to crawl cache:', e);
    
    // Simple eviction: clear all crawl cache if full
    if (e instanceof Error && e.name === 'QuotaExceededError') {
      clearCrawlCache();
    }
  }
}

export function clearCrawlCache(): void {
  try {
    Object.keys(localStorage)
      .filter(key => key.startsWith(CACHE_PREFIX))
      .forEach(key => localStorage.removeItem(key));
  } catch (e) {
    console.error('Error clearing crawl cache:', e);
  }
}
