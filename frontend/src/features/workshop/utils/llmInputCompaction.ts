import type { SourceRecord } from '../types/reportDocument';
import type { CrawledPage } from '../types/crawl';

/**
 * Compacts a crawled page into a brief string for LLM input.
 */
export function compactCrawledPageForLLM(page: CrawledPage, maxChars = 1200): string {
  const parts = [
    `URL: ${page.url}`,
    page.title ? `Title: ${page.title}` : null,
    page.source_domain ? `Domain: ${page.source_domain}` : null,
    `Content Preview:`,
    page.markdown || page.text || '(No content available)'
  ].filter(Boolean);

  return parts.join('\n').slice(0, maxChars);
}

/**
 * Compacts a SourceRecord into a brief string for LLM input.
 * Prioritizes metadata and crawled content if available.
 */
export function compactSourceForLLM(source: SourceRecord, maxChars = 1200): string {
  const metadata = (source.metadata || {}) as Record<string, unknown>;
  const content = (metadata.full_text_preview as string) || (metadata.preview as string) || source.citationText;

  const parts = [
    `ID: ${source.id}`,
    `Title: ${source.title}`,
    `Type: ${source.sourceType}`,
    `Content Depth: ${metadata.content_depth || 'snippet'}`,
    source.url ? `URL: ${source.url}` : null,
    `Citation: ${source.citationText}`,
    `Content: ${content}`
  ].filter(Boolean);

  return parts.join('\n').slice(0, maxChars);
}

/**
 * Compiles multiple sources into a list of compacted strings for candidate generation.
 */
export function compactSourcesForCandidateGeneration(
  sources: SourceRecord[],
  maxSources = 5,
  maxCharsPerSource = 1200
): string[] {
  return sources
    .slice(0, maxSources)
    .map(source => compactSourceForLLM(source, maxCharsPerSource));
}
