import React, { useState } from 'react';
import { Ban, Check, ChevronDown, ChevronUp, ExternalLink, Search } from 'lucide-react';
import { Button } from '../../../components/ui/button';
import { cn } from '../../../lib/cn';
import type { ResearchCandidate, SourceRecord } from '../types/reportDocument';
import { buildCitationText } from '../adapters/sourceAdapter';
import { REPORT_SECTION_LABELS } from '../utils/messageFormatters';

interface ResearchCandidateCardProps {
  candidate: ResearchCandidate;
  sources?: SourceRecord[];
  className?: string;
  onUse: (candidate: ResearchCandidate) => void;
  onRefine?: (candidate: ResearchCandidate) => void;
  onExclude?: (candidate: ResearchCandidate) => void;
  onViewSources?: (candidate: ResearchCandidate) => void;
}

const confidenceLabel: Record<ResearchCandidate['confidence'], string> = {
  high: '높음',
  medium: '중간',
  low: '주의',
};

export function ResearchCandidateCard({
  candidate,
  sources = [],
  className,
  onUse,
  onRefine,
  onExclude,
  onViewSources,
}: ResearchCandidateCardProps) {
  const [showSources, setShowSources] = useState(false);
  const linkedSources = sources.filter((source) => candidate.sourceIds.includes(source.id));
  const sourceCount = linkedSources.length || candidate.sourceIds.length;
  const hasMissingSource = sourceCount === 0;

  return (
    <article className={cn('rounded-xl border border-slate-200 bg-white p-4 shadow-sm', className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="mb-1 text-[11px] font-black uppercase tracking-wide text-blue-600">자료 후보</p>
          <h3 className="text-sm font-black leading-5 text-slate-900">{candidate.title}</h3>
          <p className="mt-1 text-xs font-bold text-slate-500">
            넣을 위치: {REPORT_SECTION_LABELS[candidate.sectionTarget] || candidate.sectionTarget}
          </p>
        </div>
        <span
          className={cn(
            'rounded-lg px-2 py-1 text-[11px] font-black',
            candidate.confidence === 'high' && 'bg-emerald-50 text-emerald-700',
            candidate.confidence === 'medium' && 'bg-blue-50 text-blue-700',
            candidate.confidence === 'low' && 'bg-amber-50 text-amber-700',
          )}
        >
          신뢰도 {confidenceLabel[candidate.confidence]}
        </span>
      </div>

      <p className="mt-3 text-sm font-medium leading-6 text-slate-700">{candidate.summary}</p>
      <p className="mt-2 text-xs leading-5 text-slate-600">
        <span className="font-black text-slate-800">왜 유용한가: </span>
        {candidate.whyUseful}
      </p>

      {candidate.cautionNote || hasMissingSource ? (
        <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs font-medium leading-5 text-amber-900">
          {candidate.cautionNote || '연결된 출처가 없어 적용 전 출처 보완이 필요합니다.'}
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap gap-1.5">
        <span
          className={cn(
            'rounded-lg px-2 py-1 text-[11px] font-black',
            sourceCount ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600',
          )}
        >
          {sourceCount ? `출처 ${sourceCount}개` : '출처 필요'}
        </span>
        {linkedSources.slice(0, 2).map((source) => (
          <span key={source.id} className="max-w-full truncate rounded-lg bg-slate-100 px-2 py-1 text-[11px] font-bold text-slate-600">
            {source.title}
          </span>
        ))}
      </div>

      {linkedSources.length > 0 ? (
        <button
          type="button"
          onClick={() => {
            setShowSources((value) => !value);
            onViewSources?.(candidate);
          }}
          className="mt-3 inline-flex items-center gap-1.5 text-xs font-black text-blue-700 hover:text-blue-900"
        >
          {showSources ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          출처 보기
        </button>
      ) : null}

      {showSources ? (
        <div className="mt-3 space-y-2 rounded-lg border border-slate-100 bg-slate-50 p-3">
          {linkedSources.map((source) => (
            <div key={source.id} className="text-xs leading-5 text-slate-700">
              <p className="font-bold text-slate-900">{source.title}</p>
              <p>{buildCitationText(source, 'korean_school')}</p>
              {source.url ? (
                <a className="inline-flex items-center gap-1 font-bold text-blue-700" href={source.url} target="_blank" rel="noreferrer">
                  원문 열기 <ExternalLink size={12} />
                </a>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}

      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        <Button size="sm" variant="primary" onClick={() => onUse(candidate)}>
          <Check size={14} />
          이 후보 사용
        </Button>
        <Button size="sm" variant="secondary" onClick={() => onRefine?.(candidate)}>
          <Search size={14} />
          더 구체화
        </Button>
        <Button size="sm" variant="ghost" onClick={() => onExclude?.(candidate)}>
          <Ban size={14} />
          제외
        </Button>
      </div>
    </article>
  );
}
