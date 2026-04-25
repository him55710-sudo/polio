import { api } from '../../../lib/api';
import type { ResearchCrawlResponse } from '../types/crawl';

export type ResearchSearchSource = 'semantic' | 'kci' | 'live_web' | 'both';

export interface SearchResearchPapersParams {
  query: string;
  limit?: number;
  source?: ResearchSearchSource;
}

export interface ScholarPaper {
  title?: string;
  abstract?: string;
  authors?: Array<string | { name?: string }>;
  year?: number | string | null;
  citationCount?: number;
  citation_count?: number;
  url?: string | null;
  source_type?: string;
  source_label?: string;
  source_provider?: string;
  source_domain?: string;
  freshness_label?: string;
  retrieved_at?: string | null;
  requested_source?: string;
  [key: string]: unknown;
}

export interface ScholarSearchResult {
  query: string;
  total: number;
  papers: ScholarPaper[];
  source?: string;
  [key: string]: unknown;
}

export interface ResearchIngestItem {
  source_type: 'web_article' | 'youtube_transcript' | 'paper' | 'pdf_document';
  source_classification?: string;
  title?: string | null;
  canonical_url?: string | null;
  text?: string | null;
  html_content?: string | null;
  transcript_segments?: string[];
  abstract?: string | null;
  extracted_text?: string | null;
  publisher?: string | null;
  author_names?: string[];
  published_on?: string | null;
  external_id?: string | null;
  usage_note?: string | null;
  copyright_note?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ResearchDocument {
  id: string;
  project_id: string;
  provenance_type: string;
  source_type: string;
  source_classification: string;
  trust_rank: number;
  title: string;
  canonical_url: string | null;
  external_id: string | null;
  publisher: string | null;
  published_on: string | null;
  usage_note: string | null;
  copyright_note: string | null;
  content_hash: string;
  parser_name: string;
  status: string;
  last_error: string | null;
  author_names: string[];
  source_metadata: Record<string, unknown>;
  chunk_count: number;
  word_count: number;
  ingested_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResearchChunk {
  id: string;
  document_id: string;
  project_id: string;
  provenance_type: string;
  chunk_index: number;
  char_start: number;
  char_end: number;
  token_estimate: number;
  content_text: string;
  embedding_model: string | null;
  created_at: string;
}

export interface ResearchIngestResponse {
  documents: ResearchDocument[];
  jobs: Array<Record<string, unknown>>;
}

export class ResearchClientError extends Error {
  constructor(
    message: string,
    public readonly cause?: unknown,
  ) {
    super(message);
    this.name = 'ResearchClientError';
  }
}

export async function searchResearchPapers({
  query,
  limit = 5,
  source = 'semantic',
}: SearchResearchPapersParams): Promise<ScholarSearchResult> {
  try {
    return await api.get<ScholarSearchResult>('/api/v1/research/papers', {
      params: {
        query,
        limit,
        source,
      },
    });
  } catch (error) {
    throw toResearchClientError(error, '자료 검색 중 오류가 발생했습니다.');
  }
}

export async function ingestResearchSources(input: {
  projectId: string;
  items: ResearchIngestItem[];
}): Promise<ResearchIngestResponse> {
  try {
    return await api.post<ResearchIngestResponse>('/api/v1/research/sources/ingest', {
      project_id: input.projectId,
      items: input.items,
    });
  } catch (error) {
    throw toResearchClientError(error, '자료 저장 요청 중 오류가 발생했습니다.');
  }
}

export async function listResearchSources(projectId: string): Promise<ResearchDocument[]> {
  try {
    return await api.get<ResearchDocument[]>('/api/v1/research/sources', {
      params: { project_id: projectId },
    });
  } catch (error) {
    throw toResearchClientError(error, '저장된 자료 목록을 불러오지 못했습니다.');
  }
}

export async function getResearchSource(documentId: string): Promise<ResearchDocument> {
  try {
    return await api.get<ResearchDocument>(`/api/v1/research/sources/${documentId}`);
  } catch (error) {
    throw toResearchClientError(error, '자료 상세 정보를 불러오지 못했습니다.');
  }
}

export async function getResearchSourceChunks(documentId: string): Promise<ResearchChunk[]> {
  try {
    return await api.get<ResearchChunk[]>(`/api/v1/research/sources/${documentId}/chunks`);
  } catch (error) {
    throw toResearchClientError(error, '자료 본문 조각을 불러오지 못했습니다.');
  }
}

export async function crawlResearchUrls(input: {
  projectId: string;
  urls: string[];
  maxPages?: number;
  maxCharsPerPage?: number;
}): Promise<ResearchCrawlResponse> {
  try {
    return await api.post<ResearchCrawlResponse>('/api/v1/research/crawl', {
      project_id: input.projectId,
      urls: input.urls,
      max_pages: input.maxPages,
      max_chars_per_page: input.maxCharsPerPage,
    });
  } catch (error) {
    // Network or API errors are thrown, status errors in response are not
    throw toResearchClientError(error, '웹페이지 본문 추출 중 오류가 발생했습니다.');
  }
}

function toResearchClientError(error: unknown, fallbackMessage: string): ResearchClientError {
  const message = extractApiErrorMessage(error) || fallbackMessage;
  return new ResearchClientError(message, error);
}

function extractApiErrorMessage(error: unknown): string {
  if (!error || typeof error !== 'object') return '';
  const response = (error as { response?: { data?: unknown } }).response;
  const data = response?.data;
  if (typeof data === 'string') return data;
  if (data && typeof data === 'object') {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map(String).join('\n');
    const message = (data as { message?: unknown }).message;
    if (typeof message === 'string') return message;
  }
  if (error instanceof Error) return error.message;
  return '';
}
