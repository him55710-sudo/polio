export interface CrawledPage {
  url: string;
  title?: string | null;
  text?: string | null;
  markdown?: string | null;
  extracted_at: string;
  provider: string;
  status: "ok" | "error" | "unavailable" | "skipped";
  error?: string | null;
  source_domain?: string | null;
  char_count: number;
}

export interface ResearchCrawlRequest {
  project_id: string;
  urls: string[];
  max_pages?: number;
  max_chars_per_page?: number;
}

export interface ResearchCrawlResponse {
  pages: CrawledPage[];
  ok_count: number;
  error_count: number;
  unavailable_count: number;
  skipped_count: number;
  message?: string | null;
}
