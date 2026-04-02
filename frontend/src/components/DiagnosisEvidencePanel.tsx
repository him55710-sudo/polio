import React from 'react';
import { type DiagnosisCitation, type DiagnosisPolicyFlag } from '../lib/diagnosis';
import { EmptyState, SectionCard, StatusBadge, SurfaceCard, WorkflowNotice } from './primitives';

interface DiagnosisEvidencePanelProps {
  citations: DiagnosisCitation[];
  reviewRequired: boolean;
  policyFlags: DiagnosisPolicyFlag[];
  responseTraceId?: string | null;
}

function severityVariant(severity: string): 'neutral' | 'warning' | 'danger' {
  const normalized = severity.toLowerCase();
  if (normalized === 'critical') return 'danger';
  if (normalized === 'high') return 'warning';
  return 'neutral';
}

export function DiagnosisEvidencePanel({
  citations,
  reviewRequired,
  policyFlags,
  responseTraceId,
}: DiagnosisEvidencePanelProps) {
  if (!citations.length && !reviewRequired && !policyFlags.length && !responseTraceId) {
    return null;
  }

  return (
    <div data-testid="diagnosis-evidence-panel" className="grid gap-6 lg:grid-cols-2">
      <SectionCard
        title="근거 인용"
        description="진단 문장이 어떤 문서 근거에서 생성되었는지 확인합니다."
        eyebrow="근거"
        actions={
          <StatusBadge status={citations.length ? 'active' : 'neutral'}>
            {citations.length ? `${citations.length}개 근거` : '근거 없음'}
          </StatusBadge>
        }
      >
        {citations.length ? (
          <div className="space-y-3">
            {citations.map(citation => (
              <SurfaceCard
                key={`${citation.document_chunk_id || citation.source_label}-${citation.page_number || 'na'}`}
                tone="muted"
                padding="sm"
              >
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <StatusBadge status="neutral">{citation.source_label}</StatusBadge>
                  {citation.page_number ? <StatusBadge status="active">{citation.page_number}페이지</StatusBadge> : null}
                  <StatusBadge status="success">관련도 {Math.round(citation.relevance_score * 100)}%</StatusBadge>
                </div>
                <p className="text-sm font-medium italic leading-6 text-slate-600">"{citation.excerpt}"</p>
              </SurfaceCard>
            ))}
          </div>
        ) : (
          <EmptyState title="표시할 근거가 없습니다" description="문서 업로드와 진단 실행 상태를 먼저 확인해 주세요." />
        )}
      </SectionCard>

      <SectionCard
        title="안전성 및 검토 상태"
        description="추가 검토 필요 여부와 정책 플래그를 확인합니다."
        eyebrow="신뢰"
        actions={<StatusBadge status={reviewRequired ? 'warning' : 'success'}>{reviewRequired ? '검토 필요' : '안정'}</StatusBadge>}
        data-testid="diagnosis-review-panel"
      >
        <WorkflowNotice
          tone={reviewRequired ? 'warning' : 'success'}
          title={reviewRequired ? '추가 검토가 필요합니다' : '추가 검토가 필요하지 않습니다'}
          description={
            reviewRequired
              ? '근거 문장 연결과 표현 정확도를 다시 확인한 뒤 결과를 반영해 주세요.'
              : '현재 상태에서는 별도 정책 경고 없이 결과를 활용할 수 있습니다.'
          }
        />

        {responseTraceId ? <p className="text-[11px] font-medium text-slate-400">추적 ID: {responseTraceId}</p> : null}

        {policyFlags.length ? (
          <div className="space-y-2">
            {policyFlags.map(flag => (
              <SurfaceCard key={flag.id} padding="sm">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <p className="text-sm font-bold text-slate-800">{flag.code}</p>
                  <StatusBadge status={severityVariant(flag.severity)}>{flag.severity}</StatusBadge>
                </div>
                <p className="text-sm font-medium leading-6 text-slate-600">{flag.detail}</p>
              </SurfaceCard>
            ))}
          </div>
        ) : (
          <EmptyState title="정책 플래그가 없습니다" description="현재 진단 결과에는 정책 경고가 감지되지 않았습니다." />
        )}
      </SectionCard>
    </div>
  );
}
