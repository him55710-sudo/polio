export interface ArchiveItem {
  id: string;
  projectId: string | null;
  workshopId?: string | null;
  kind?: 'report' | 'workshop';
  title: string;
  subject: string;
  summary?: string;
  createdAt: string;
  updatedAt?: string;
  contentMarkdown: string;
  structuredDraft?: unknown;
  chatMessages?: Array<{
    id: string;
    role: 'user' | 'foli';
    content: string;
    createdAt?: string;
  }>;
}

const STORAGE_KEY = 'uni_foli_archive_items';
const BACKEND_CONNECTION_ERROR_PATTERNS = [
  /백엔드 서버에 연결할 수 없습니다/i,
  /API 서버 주소,\s*배포 상태,\s*CORS 설정/i,
  /backend server/i,
  /network\s*error/i,
  /failed to fetch/i,
];

interface DeriveArchiveTitleInput {
  contentMarkdown?: string | null;
  structuredDraft?: unknown;
  fallbackTitle?: string | null;
  subject?: string | null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function asText(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

export function isBackendConnectionErrorContent(value?: string | null): boolean {
  const text = (value || '').trim();
  if (!text) return false;
  return BACKEND_CONNECTION_ERROR_PATTERNS.some((pattern) => pattern.test(text));
}

export function isGenericArchiveTitle(value?: string | null): boolean {
  const normalized = (value || '').trim().toLowerCase().replace(/\.(hwpx|pdf|md|txt)$/i, '');
  if (!normalized) return true;
  return [
    'draft',
    'untitled',
    '제목 없음',
    '임시 저장',
    '임시 초안',
    '워크숍 보고서',
    '탐구 보고서 초안',
    '생기부 기반 탐구 보고서',
    'local',
  ].includes(normalized);
}

function extractMarkdownHeading(markdown?: string | null): string {
  const text = (markdown || '').trim();
  if (!text || isBackendConnectionErrorContent(text)) return '';

  const heading = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => /^#{1,3}\s+\S/.test(line));

  return heading ? heading.replace(/^#{1,3}\s+/, '').replace(/\*\*/g, '').trim() : '';
}

function extractStructuredDraftTitle(raw: unknown): string {
  const draft = asRecord(raw);
  if (!draft) return '';

  const directTitle =
    asText(draft.title) ||
    asText(draft.topic) ||
    asText(draft.subject) ||
    asText(draft.research_title) ||
    asText(draft.researchTitle);
  if (directTitle) return directTitle;

  const blocks = Array.isArray(draft.blocks) ? draft.blocks : [];
  for (const block of blocks) {
    const record = asRecord(block);
    if (!record) continue;
    const candidate =
      asText(record.title) ||
      asText(record.heading) ||
      asText(record.content)
        .split(/\r?\n/)
        .map((line) => line.trim())
        .find((line) => line.length >= 6);
    if (candidate) return candidate;
  }

  return '';
}

function cleanupTitle(title: string): string {
  return title
    .replace(/^["'`]+|["'`]+$/g, '')
    .replace(/^탐구\s*주제\s*[:：-]\s*/i, '')
    .replace(/^주제\s*[:：-]\s*/i, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 80);
}

export function deriveArchiveTitle(input: DeriveArchiveTitleInput): string {
  const candidates = [
    extractMarkdownHeading(input.contentMarkdown),
    extractStructuredDraftTitle(input.structuredDraft),
    input.fallbackTitle || '',
    input.subject ? `${input.subject} 탐구 보고서` : '',
  ];

  const title = candidates
    .map(cleanupTitle)
    .find((candidate) => candidate && !isGenericArchiveTitle(candidate) && !isBackendConnectionErrorContent(candidate));

  return title || '생기부 기반 탐구 보고서';
}

function structuredDraftToArchiveMarkdown(raw: unknown): string {
  const draft = asRecord(raw);
  if (!draft) return '';

  const title = extractStructuredDraftTitle(draft);
  const blocks = Array.isArray(draft.blocks) ? draft.blocks : [];
  const blockMarkdown = blocks
    .map((block) => {
      const record = asRecord(block);
      if (!record) return '';
      const heading = asText(record.title) || asText(record.heading) || asText(record.label);
      const content = asText(record.content) || asText(record.markdown) || asText(record.body);
      if (!heading && !content) return '';
      return [heading ? `## ${heading}` : '', content].filter(Boolean).join('\n\n');
    })
    .filter(Boolean)
    .join('\n\n');

  if (!title && !blockMarkdown) return '';
  return [`# ${title || '생기부 기반 탐구 보고서'}`, blockMarkdown].filter(Boolean).join('\n\n');
}

function chatMessagesToArchiveMarkdown(item: ArchiveItem): string {
  const messages = item.chatMessages || [];
  if (messages.length === 0) return '';
  return messages
    .filter((message) => message.content.trim())
    .map((message) => `## ${message.role === 'user' ? '학생 요청' : 'Foli 응답'}\n\n${message.content.trim()}`)
    .join('\n\n');
}

function buildArchiveSummary(contentMarkdown?: string | null): string {
  const text = (contentMarkdown || '')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/[-*]\s+/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  if (!text || isBackendConnectionErrorContent(text)) return '';
  return text.slice(0, 120);
}

export function resolveArchiveDownloadContent(item: ArchiveItem): string {
  const primary = (item.contentMarkdown || '').trim();
  if (primary && !isBackendConnectionErrorContent(primary)) return primary;

  const structured = structuredDraftToArchiveMarkdown(item.structuredDraft).trim();
  if (structured && !isBackendConnectionErrorContent(structured)) return structured;

  const chatMarkdown = chatMessagesToArchiveMarkdown(item).trim();
  if (chatMarkdown && !isBackendConnectionErrorContent(chatMarkdown)) return chatMarkdown;

  return '';
}

function resolveContentForSave(item: ArchiveItem, previous?: ArchiveItem): string {
  const incoming = (item.contentMarkdown || '').trim();
  if (incoming && !isBackendConnectionErrorContent(incoming)) return incoming;

  const previousContent = (previous?.contentMarkdown || '').trim();
  if (previousContent && !isBackendConnectionErrorContent(previousContent)) return previousContent;

  return resolveArchiveDownloadContent(item);
}

function readItems(): ArchiveItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ArchiveItem[];
    if (!Array.isArray(parsed)) return [];
    return parsed;
  } catch {
    return [];
  }
}

function writeItems(items: ArchiveItem[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

export function listArchiveItems(): ArchiveItem[] {
  return readItems().sort((a, b) => ((a.updatedAt || a.createdAt) < (b.updatedAt || b.createdAt) ? 1 : -1));
}

export function getArchiveItem(id: string): ArchiveItem | null {
  return readItems().find((item) => item.id === id) ?? null;
}

export function saveArchiveItem(item: ArchiveItem): void {
  const items = readItems();
  const previous = items.find((entry) => entry.id === item.id);
  const contentMarkdown = resolveContentForSave(item, previous);
  const title = isGenericArchiveTitle(item.title)
    ? deriveArchiveTitle({
        contentMarkdown,
        structuredDraft: item.structuredDraft ?? previous?.structuredDraft,
        fallbackTitle: previous?.title || item.title,
        subject: item.subject || previous?.subject,
      })
    : item.title.trim();
  const merged: ArchiveItem = {
    ...previous,
    ...item,
    title,
    contentMarkdown,
    summary: item.summary || previous?.summary || buildArchiveSummary(contentMarkdown),
    createdAt: previous?.createdAt || item.createdAt,
    updatedAt: item.updatedAt || new Date().toISOString(),
  };
  const next = [merged, ...items.filter((entry) => entry.id !== item.id)].slice(0, 100);
  writeItems(next);
}

export function updateArchiveItemTitle(id: string, nextTitle: string): ArchiveItem | null {
  const items = readItems();
  const current = items.find((item) => item.id === id);
  const title = cleanupTitle(nextTitle);
  if (!current || !title) return null;

  const updated: ArchiveItem = {
    ...current,
    title,
    updatedAt: new Date().toISOString(),
  };
  writeItems([updated, ...items.filter((item) => item.id !== id)]);
  return updated;
}

export function downloadArchiveAsText(item: ArchiveItem, format: 'hwpx' | 'pdf'): void {
  const content = resolveArchiveDownloadContent(item);
  if (!content) {
    throw new Error('다운로드할 문서 내용이 아직 저장되지 않았습니다. 전문편집기에서 저장한 뒤 다시 시도해 주세요.');
  }

  const title = deriveArchiveTitle({
    contentMarkdown: content,
    structuredDraft: item.structuredDraft,
    fallbackTitle: item.title,
    subject: item.subject,
  });
  const header = [
    `# ${title}`,
    '',
    `- Subject: ${item.subject}`,
    `- Created: ${new Date(item.createdAt).toLocaleString()}`,
    item.projectId ? `- Project ID: ${item.projectId}` : '- Project ID: local',
    '',
  ].join('\n');

  const payload = `${header}${content}`.trim();
  const blob = new Blob([payload], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${title.replace(/[^\w\-\uAC00-\uD7A3]+/g, '_')}.${format}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
export function deleteArchiveItem(id: string): void {
  const items = readItems();
  const next = items.filter((item) => item.id !== id);
  writeItems(next);
}
