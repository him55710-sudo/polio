import type {
  ReportFormatProfile,
  SourceRecord,
  UniFoliReportSectionId,
} from '../types/reportDocument';
import type { CrawledPage } from '../types/crawl';

export type CitationStyle = ReportFormatProfile['citation']['style'] | 'simple_url';

const SOURCE_SECTION_ORDER: UniFoliReportSectionId[] = [
  'cover',
  'table_of_contents',
  'motivation',
  'research_purpose',
  'research_question',
  'background_theory',
  'prior_research',
  'research_method',
  'research_process',
  'data_analysis',
  'result',
  'conclusion',
  'limitation',
  'future_research',
  'student_record_connection',
  'references',
  'appendix',
];

export function convertPaperResultToSourceRecord(result: Record<string, unknown>): SourceRecord {
  const url = stringValue(result.url) || stringValue(result.link);
  const authors = normalizeAuthors(result.authors);
  const sourceType = normalizePaperSourceType(result);
  const record: SourceRecord = {
    id: stringValue(result.id) || stringValue(result.external_id) || stableSourceId(result),
    title: stringValue(result.title) || '제목 미상',
    authors,
    year: normalizeYear(result.year) || normalizeYear(result.published_year) || normalizeYear(result.publication_year),
    publisher: stringValue(result.publisher) || stringValue(result.source_label) || stringValue(result.source_domain),
    journal: stringValue(result.journal) || stringValue(result.venue),
    url,
    accessedAt: url ? stringValue(result.accessedAt) || stringValue(result.accessed_at) || todayIsoDate() : '',
    sourceType,
    reliability: normalizeReliability(stringValue(result.reliability) || reliabilityFromResult(result)),
    usedInSections: [],
    citationText: '',
  };
  return { ...record, citationText: buildCitationText(record, 'korean_school') };
}

export function convertResearchDocumentToSourceRecord(document: Record<string, unknown>): SourceRecord {
  const url = stringValue(document.canonical_url) || stringValue(document.url) || stringValue(document.source_url);
  const metadata = isRecord(document.source_metadata) ? document.source_metadata : {};
  const record: SourceRecord = {
    id: stringValue(document.id) || stableSourceId(document),
    title: stringValue(document.title) || '제목 미상',
    authors: normalizeAuthors(document.author_names || document.authors || metadata.authors),
    year:
      normalizeYear(document.published_on) ||
      normalizeYear(metadata.year) ||
      normalizeYear(metadata.published_year),
    publisher: stringValue(document.publisher) || stringValue(metadata.publisher) || stringValue(metadata.site_name),
    journal: stringValue(metadata.journal) || stringValue(metadata.venue),
    url,
    accessedAt:
      url
        ? normalizeDateOnly(document.ingested_at) ||
          normalizeDateOnly(document.created_at) ||
          stringValue(metadata.accessedAt) ||
          todayIsoDate()
        : '',
    sourceType: normalizeSourceType(stringValue(document.source_type) || stringValue(metadata.source_type)),
    reliability: reliabilityFromTrustRank(document.trust_rank),
    usedInSections: [],
    citationText: '',
  };
  return { ...record, citationText: buildCitationText(record, 'korean_school') };
}

export function convertResearchChunkToSourceRecord(
  chunk: Record<string, unknown>,
  document?: Record<string, unknown> | SourceRecord | null,
): SourceRecord {
  if (document && isSourceRecord(document)) {
    return document;
  }
  const base = document ? convertResearchDocumentToSourceRecord(document as Record<string, unknown>) : null;
  const record: SourceRecord = {
    id: base?.id || stringValue(chunk.document_id) || stableSourceId(chunk),
    title: base?.title || `자료 조각 ${stringValue(chunk.chunk_index) || ''}`.trim(),
    authors: base?.authors || [],
    year: base?.year || '',
    publisher: base?.publisher || '',
    journal: base?.journal || '',
    url: base?.url || '',
    accessedAt: base?.accessedAt || '',
    sourceType: base?.sourceType || 'report',
    reliability: base?.reliability || 'medium',
    usedInSections: base?.usedInSections || [],
    citationText: '',
  };
  return { ...record, citationText: buildCitationText(record, 'korean_school') };
}

export function buildCitationText(source: SourceRecord, style: CitationStyle = 'korean_school'): string {
  if (source.citationText?.trim()) {
    return source.citationText.trim();
  }

  const authorsKorean = source.authors.length ? source.authors.join(', ') : '저자 미상';
  const authorsApa = source.authors.length ? source.authors.join(', ') : 'Unknown author';
  const yearKorean = source.year || '연도 미상';
  const yearApa = source.year || 'n.d.';
  const title = source.title || '제목 미상';
  const container = source.journal || source.publisher || '';
  const url = source.url || '';

  if (style === 'simple_url') {
    return [title, url].filter(Boolean).join(' - ') || '출처 정보 부족';
  }

  if (style === 'apa') {
    const parts = [`${authorsApa} (${yearApa}).`, title, container].filter(Boolean);
    const suffix = source.sourceType === 'website' && source.accessedAt
      ? `${url} (accessed ${source.accessedAt})`
      : url;
    return [...parts, suffix].filter(Boolean).join(' ');
  }

  const urlText = url
    ? source.sourceType === 'website' && source.accessedAt
      ? `${url} (접속일: ${source.accessedAt})`
      : url
    : '';
  return [`${authorsKorean} (${yearKorean}).`, title, container, urlText].filter(Boolean).join(' ');
}

export function dedupeSourceRecords(sources: SourceRecord[]): SourceRecord[] {
  const seen = new Map<string, SourceRecord>();
  for (const source of sources) {
    const normalized = { ...source, citationText: buildCitationText(source, 'korean_school') };
    const key = sourceDedupKey(normalized);
    const existing = seen.get(key);
    if (!existing) {
      seen.set(key, normalized);
      continue;
    }

    seen.set(key, {
      ...existing,
      authors: existing.authors.length ? existing.authors : normalized.authors,
      year: existing.year || normalized.year,
      publisher: existing.publisher || normalized.publisher,
      journal: existing.journal || normalized.journal,
      url: existing.url || normalized.url,
      accessedAt: existing.accessedAt || normalized.accessedAt,
      reliability: pickHigherReliability(existing.reliability, normalized.reliability),
      usedInSections: uniqueSections([...existing.usedInSections, ...normalized.usedInSections]),
      citationText: existing.citationText || normalized.citationText,
    });
  }
  return [...seen.values()];
}

export function updateSourceUsage(source: SourceRecord, sectionId: UniFoliReportSectionId): SourceRecord;
export function updateSourceUsage(
  sources: SourceRecord[],
  sourceIds: string[],
  sectionId: UniFoliReportSectionId,
): SourceRecord[];
export function updateSourceUsage(
  sourceOrSources: SourceRecord | SourceRecord[],
  sectionOrIds: UniFoliReportSectionId | string[],
  maybeSectionId?: UniFoliReportSectionId,
): SourceRecord | SourceRecord[] {
  if (Array.isArray(sourceOrSources)) {
    const ids = new Set(Array.isArray(sectionOrIds) ? sectionOrIds : []);
    const sectionId = maybeSectionId;
    if (!sectionId) return sourceOrSources;
    return sourceOrSources.map((source) => (ids.has(source.id) ? updateSourceUsage(source, sectionId) : source));
  }

  const sectionId = sectionOrIds as UniFoliReportSectionId;
  return {
    ...sourceOrSources,
    usedInSections: uniqueSections([...sourceOrSources.usedInSections, sectionId]),
  };
}

export function groupSourcesBySection(sources: SourceRecord[]): Record<UniFoliReportSectionId, SourceRecord[]> {
  const grouped = SOURCE_SECTION_ORDER.reduce(
    (acc, sectionId) => {
      acc[sectionId] = [];
      return acc;
    },
    {} as Record<UniFoliReportSectionId, SourceRecord[]>,
  );
  for (const source of sources) {
    for (const sectionId of source.usedInSections) {
      grouped[sectionId]?.push(source);
    }
  }
  return grouped;
}

export function buildReferencesMarkdown(
  sources: SourceRecord[],
  formatProfile?: Pick<ReportFormatProfile, 'citation'> | ReportFormatProfile,
): string {
  const style = formatProfile?.citation?.style || 'korean_school';
  const deduped = dedupeSourceRecords(sources);
  if (deduped.length === 0) {
    return '참고문헌 없음';
  }
  return deduped
    .slice()
    .sort((a, b) => buildCitationText(a, style).localeCompare(buildCitationText(b, style), 'ko'))
    .map((source, index) => `${index + 1}. ${buildCitationText(source, style)}`)
    .join('\n');
}

export function convertCrawledPageToSourceRecord(page: CrawledPage): SourceRecord | null {
  if (page.status !== 'ok') return null;

  const title = page.title || page.source_domain || page.url;
  const record: SourceRecord = {
    id: `crawl-${stableSourceId({ title: page.title, url: page.url })}`,
    title,
    authors: [],
    year: page.extracted_at.slice(0, 4),
    publisher: page.source_domain || '',
    journal: '',
    url: page.url,
    accessedAt: page.extracted_at.slice(0, 10),
    sourceType: 'website',
    reliability: 'medium',
    usedInSections: [],
    citationText: '',
    metadata: {
      preview: page.markdown?.slice(0, 500) || page.text?.slice(0, 500),
      full_text_preview: page.text?.slice(0, 2000),
      provider: page.provider,
      content_depth: 'full_text',
    },
  };
  return { ...record, citationText: buildCitationText(record, 'korean_school') };
}

export function mergeCrawledPageIntoSourceRecord(source: SourceRecord, page: CrawledPage): SourceRecord {
  if (page.status !== 'ok') return source;

  const updatedMetadata = {
    ...(source.metadata || {}),
    preview: page.markdown?.slice(0, 500) || page.text?.slice(0, 500),
    full_text_preview: page.text?.slice(0, 2000),
    crawled_at: page.extracted_at,
    crawl_provider: page.provider,
    content_depth: 'full_text',
  };

  const newTitle = !source.title || source.title === '제목 미상' ? page.title || source.title : source.title;

  return {
    ...source,
    title: newTitle,
    publisher: source.publisher || page.source_domain || '',
    metadata: updatedMetadata,
  };
}

export const researchPaperResultToSourceRecord = convertPaperResultToSourceRecord;
export const researchSourceDocumentToSourceRecord = convertResearchDocumentToSourceRecord;

export function sourceRecordToCitationText(source: SourceRecord): string {
  return buildCitationText(source, 'apa');
}

function normalizeAuthors(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (isRecord(item)) return stringValue(item.name) || stringValue(item.author) || stringValue(item.title);
        return stringValue(item);
      })
      .filter(Boolean);
  }
  const text = stringValue(value);
  return text ? text.split(/\s*,\s*/).filter(Boolean) : [];
}

function normalizePaperSourceType(raw: Record<string, unknown>): SourceRecord['sourceType'] {
  const type = stringValue(raw.source_type) || stringValue(raw.sourceType) || stringValue(raw.requested_source);
  if (type.includes('web') || type === 'live_web') return 'website';
  if (type.includes('news')) return 'news';
  if (type.includes('report')) return 'report';
  if (type.includes('dataset')) return 'dataset';
  return 'paper';
}

function normalizeSourceType(value: string): SourceRecord['sourceType'] {
  if (value === 'paper') return 'paper';
  if (value === 'book') return 'book';
  if (value === 'news') return 'news';
  if (value === 'report' || value === 'pdf_document') return 'report';
  if (value === 'dataset') return 'dataset';
  if (value === 'web_article' || value === 'website' || value === 'youtube_transcript') return 'website';
  return 'report';
}

function normalizeReliability(value: string): SourceRecord['reliability'] {
  if (value === 'low' || value === 'medium' || value === 'high') return value;
  return 'medium';
}

function reliabilityFromResult(raw: Record<string, unknown>): SourceRecord['reliability'] {
  const citationCount = Number(raw.citationCount ?? raw.citation_count ?? 0);
  const provider = stringValue(raw.source_provider) || stringValue(raw.source);
  if (citationCount >= 20 || provider === 'semantic') return 'high';
  if (provider === 'live_web') return 'medium';
  return 'medium';
}

function reliabilityFromTrustRank(value: unknown): SourceRecord['reliability'] {
  const rank = Number(value ?? 0);
  if (rank >= 80) return 'high';
  if (rank > 0 && rank < 40) return 'low';
  return 'medium';
}

function pickHigherReliability(
  left: SourceRecord['reliability'],
  right: SourceRecord['reliability'],
): SourceRecord['reliability'] {
  const rank = { low: 0, medium: 1, high: 2 } as const;
  return rank[right] > rank[left] ? right : left;
}

function sourceDedupKey(source: SourceRecord): string {
  const url = source.url.trim().toLowerCase().replace(/\/+$/, '');
  if (url) return `url:${url}`;
  return `title:${source.title.trim().toLowerCase()}::${source.year || 'unknown'}`;
}

function uniqueSections(values: UniFoliReportSectionId[]): UniFoliReportSectionId[] {
  return [...new Set(values)];
}

function stringValue(value: unknown): string {
  return typeof value === 'string' || typeof value === 'number' ? String(value).trim() : '';
}

function normalizeYear(value: unknown): string {
  const text = stringValue(value);
  const match = text.match(/\d{4}/);
  return match?.[0] || '';
}

function normalizeDateOnly(value: unknown): string {
  const text = stringValue(value);
  return text.match(/^\d{4}-\d{2}-\d{2}/)?.[0] || '';
}

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function stableSourceId(raw: Record<string, unknown>): string {
  const seed = [raw.title, raw.url, raw.canonical_url, raw.year, raw.external_id]
    .map((value) => stringValue(value))
    .join('|') || cryptoSafeRandom();
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) >>> 0;
  }
  return `source-${hash.toString(36)}`;
}

function cryptoSafeRandom(): string {
  return typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function isSourceRecord(value: unknown): value is SourceRecord {
  return isRecord(value) && typeof value.id === 'string' && Array.isArray(value.usedInSections);
}
