import React, { useMemo, useState } from 'react';
import { AlertTriangle, BookOpen, CheckCircle2, Plus, Quote, RefreshCw } from 'lucide-react';
import { cn } from '../../lib/cn';
import type { CitationStyleId, CitationSourceType, UniFoliCitationSource } from './model/documentModel';
import {
  buildBibliographyMarkdown,
  createEmptyCitationSource,
  detectNeedsCitationSentences,
  formatInlineCitation,
} from './citations/citationUtils';

interface CitationPanelProps {
  sources: UniFoliCitationSource[];
  citationStyle: CitationStyleId;
  documentMarkdown: string;
  onCitationStyleChange: (style: CitationStyleId) => void;
  onSourcesChange: (sources: UniFoliCitationSource[]) => void;
  onInsertCitation: (text: string, source: UniFoliCitationSource) => void;
  onUpdateBibliography: (markdown: string) => void;
  className?: string;
}

const SOURCE_TYPES: Array<{ id: CitationSourceType; label: string }> = [
  { id: 'website', label: '웹사이트' },
  { id: 'paper', label: '논문' },
  { id: 'book', label: '도서' },
  { id: 'report', label: '보고서' },
  { id: 'news', label: '뉴스 기사' },
  { id: 'other', label: '기타' },
];

const CITATION_STYLES: Array<{ id: CitationStyleId; label: string }> = [
  { id: 'korean_report', label: '한국어 보고서형' },
  { id: 'apa', label: 'APA' },
  { id: 'mla', label: 'MLA' },
  { id: 'chicago', label: 'Chicago' },
  { id: 'numbered', label: '번호형' },
];

export function CitationPanel({
  sources,
  citationStyle,
  documentMarkdown,
  onCitationStyleChange,
  onSourcesChange,
  onInsertCitation,
  onUpdateBibliography,
  className,
}: CitationPanelProps) {
  const [draft, setDraft] = useState<UniFoliCitationSource>(() => createEmptyCitationSource());
  const needsCitation = useMemo(() => detectNeedsCitationSentences(documentMarkdown), [documentMarkdown]);

  const saveDraft = () => {
    const title = draft.title.trim();
    if (!title) return;
    onSourcesChange([
      ...sources,
      {
        ...draft,
        id: draft.id || `src-${Date.now()}`,
        title,
        authors: draft.authors.map((author) => author.trim()).filter(Boolean),
        verificationStatus: draft.verificationStatus || 'needs_verification',
      },
    ]);
    setDraft(createEmptyCitationSource());
  };

  return (
    <aside className={cn('space-y-4', className)}>
      <div>
        <div className="mb-2 flex items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-indigo-600">
          <BookOpen size={14} />
          Citation Manager
        </div>
        <p className="text-sm font-medium leading-6 text-slate-600">
          직접 추가한 출처와 AI가 제안한 출처를 구분하고, 검증이 필요한 출처는 참고문헌에 표시합니다.
        </p>
      </div>

      <label className="block">
        <span className="mb-1 block text-xs font-black text-slate-500">인용 스타일</span>
        <select
          value={citationStyle}
          onChange={(event) => onCitationStyleChange(event.target.value as CitationStyleId)}
          className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-bold text-slate-800 outline-none focus:border-indigo-300 focus:ring-4 focus:ring-indigo-100"
        >
          {CITATION_STYLES.map((style) => (
            <option key={style.id} value={style.id}>{style.label}</option>
          ))}
        </select>
      </label>

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-black text-slate-900">출처 추가</h3>
          <span className="rounded-full bg-white px-2 py-1 text-[11px] font-black text-slate-500">CSL 호환 필드</span>
        </div>
        <div className="grid gap-2">
          <select
            value={draft.type}
            onChange={(event) => setDraft((current) => ({ ...current, type: event.target.value as CitationSourceType }))}
            className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700"
          >
            {SOURCE_TYPES.map((type) => (
              <option key={type.id} value={type.id}>{type.label}</option>
            ))}
          </select>
          <input value={draft.title} onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))} placeholder="제목" className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700" />
          <input value={draft.authors.join(', ')} onChange={(event) => setDraft((current) => ({ ...current, authors: event.target.value.split(',') }))} placeholder="저자, 저자" className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700" />
          <div className="grid grid-cols-2 gap-2">
            <input value={draft.year} onChange={(event) => setDraft((current) => ({ ...current, year: event.target.value }))} placeholder="발행연도" className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700" />
            <input value={draft.publisher} onChange={(event) => setDraft((current) => ({ ...current, publisher: event.target.value }))} placeholder="발행기관" className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700" />
          </div>
          <input value={draft.url} onChange={(event) => setDraft((current) => ({ ...current, url: event.target.value }))} placeholder="URL" className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700" />
          <div className="grid grid-cols-2 gap-2">
            <input value={draft.accessedAt} onChange={(event) => setDraft((current) => ({ ...current, accessedAt: event.target.value }))} placeholder="접속일" className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700" />
            <input value={draft.doi} onChange={(event) => setDraft((current) => ({ ...current, doi: event.target.value }))} placeholder="DOI" className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700" />
          </div>
          <button type="button" onClick={saveDraft} disabled={!draft.title.trim()} className="mt-1 inline-flex h-9 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-3 text-xs font-black text-white transition hover:bg-indigo-700 disabled:opacity-40">
            <Plus size={14} />
            출처 저장
          </button>
        </div>
      </div>

      <div className="space-y-2">
        {sources.length ? sources.map((source, index) => (
          <div key={source.id} className="rounded-xl border border-slate-200 bg-white p-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-black text-slate-900">{source.title}</p>
                <p className="mt-1 text-xs font-medium text-slate-500">{source.authors.join(', ') || '저자 미상'} · {source.year || '연도 미상'}</p>
              </div>
              {source.verificationStatus === 'verified' ? <CheckCircle2 size={15} className="text-emerald-600" /> : <AlertTriangle size={15} className="text-amber-600" />}
            </div>
            <button type="button" onClick={() => onInsertCitation(formatInlineCitation(source, citationStyle, index), source)} className="mt-3 inline-flex h-8 w-full items-center justify-center gap-1.5 rounded-lg border border-slate-200 text-xs font-black text-slate-700 hover:bg-slate-50">
              <Quote size={13} />
              본문 인용
            </button>
          </div>
        )) : (
          <p className="rounded-xl border border-dashed border-slate-200 p-3 text-xs font-bold text-slate-500">아직 등록된 출처가 없습니다.</p>
        )}
      </div>

      <button type="button" onClick={() => onUpdateBibliography(buildBibliographyMarkdown(sources, citationStyle))} className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50 text-sm font-black text-indigo-700 hover:bg-indigo-100">
        <RefreshCw size={15} />
        참고문헌 섹션 업데이트
      </button>

      {needsCitation.length ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <p className="mb-2 inline-flex items-center gap-2 text-sm font-black text-amber-900">
            <AlertTriangle size={15} />
            출처 필요 가능 문장
          </p>
          <ul className="space-y-2 text-xs font-medium leading-5 text-amber-900">
            {needsCitation.slice(0, 4).map((sentence) => <li key={sentence}>- {sentence}</li>)}
          </ul>
        </div>
      ) : null}
    </aside>
  );
}
