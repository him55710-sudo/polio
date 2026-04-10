import React from 'react';
import { AlertTriangle, CheckCircle2, Clock3, Loader2, RefreshCw, RotateCcw } from 'lucide-react';
import { type AsyncJobRead, formatAsyncJobStatus, formatDateTime } from '../lib/diagnosis';
import { PrimaryButton, SectionCard, StatusBadge, WorkflowNotice } from './primitives';

interface AsyncJobStatusCardProps {
  job: AsyncJobRead | null;
  runStatus: string | null | undefined;
  errorMessage?: string | null;
  onRetry?: (() => void) | null;
  isRetrying?: boolean;
}

function normalizeStatus(status: string | null | undefined) {
  return (status ?? 'queued').toLowerCase();
}

function statusVariant(status: string): 'neutral' | 'active' | 'success' | 'warning' | 'danger' {
  if (status === 'succeeded') return 'success';
  if (status === 'failed') return 'danger';
  if (status === 'retrying') return 'warning';
  if (status === 'running') return 'active';
  return 'neutral';
}

function statusIcon(status: string) {
  if (status === 'succeeded') return <CheckCircle2 size={16} />;
  if (status === 'failed') return <AlertTriangle size={16} />;
  if (status === 'retrying') return <RefreshCw size={16} />;
  if (status === 'running') return <Loader2 size={16} className="animate-pulse" />;
  return <Clock3 size={16} />;
}

function progressByStatus(status: string) {
  if (status === 'queued') return 8;
  if (status === 'running') return 62;
  if (status === 'retrying') return 72;
  return 100;
}

function formatProgressText(message: string | undefined): string {
  if (!message) return '현재 분석 흐름을 점검하고 있어요.';

  const normalized = message.toLowerCase();
  if (normalized.includes('queue')) return '분석 예약이 완료되어 순서를 기다리는 중이에요.';
  if (normalized.includes('mask')) return '개인정보 보안 처리를 진행하고 있어요.';
  if (normalized.includes('pars')) return '문서 내용을 꼼꼼하게 읽어보는 중이에요.';
  if (normalized.includes('metadata') || normalized.includes('chunk')) return '문서를 꼼꼼하게 읽어보는 중이에요.';
  return message;
}

export function AsyncJobStatusCard({
  job,
  runStatus,
  errorMessage,
  onRetry,
  isRetrying = false,
}: AsyncJobStatusCardProps) {
  const status = normalizeStatus(job?.status ?? runStatus);
  const failure = job?.failure_reason || errorMessage || null;
  const progressPct = progressByStatus(status);
  const stage = (job as { progress_stage?: string } | null)?.progress_stage || formatAsyncJobStatus(status);
  const message = formatProgressText((job as { progress_message?: string } | null)?.progress_message);
  const history = ((job as { progress_history?: Array<{ stage?: string; message?: string }> } | null)?.progress_history || []).slice(-4);

  return (
    <SectionCard
      title="진단 작업 상태"
      description="현재 분석 진행 상황과 최근 업데이트를 확인할 수 있어요."
      eyebrow="진행 현황"
      data-testid="diagnosis-job-status"
      actions={(
        <StatusBadge status={statusVariant(status)}>
          <span className="inline-flex items-center gap-1">
            {statusIcon(status)}
            {formatAsyncJobStatus(status)}
          </span>
        </StatusBadge>
      )}
    >
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">현재 단계</p>
            <p className="mt-1 text-sm font-bold text-slate-800">{stage}</p>
            <p className="mt-1 text-xs font-medium text-slate-500">{message}</p>
          </div>
          <div className="text-right">
            <p className="text-lg font-bold text-slate-900">{progressPct}%</p>
            {formatDateTime(job?.updated_at || job?.completed_at) ? (
              <p className="text-[11px] font-medium text-slate-400">{formatDateTime(job?.updated_at || job?.completed_at)}</p>
            ) : null}
          </div>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-200">
          <div
            className={status === 'failed' ? 'h-full rounded-full bg-red-500' : 'h-full rounded-full bg-[#004aad] transition-[width] duration-500'}
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {history.length ? (
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">최근 기록</p>
          <div className="space-y-1.5">
            {history.map((item, index) => (
              <div key={`${item.stage || 'stage'}-${index}`} className="flex items-start gap-2 text-xs">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-400" />
                <p className="font-semibold text-slate-600">
                  <span className="mr-2 font-bold text-slate-700">{item.stage || '단계'}</span>
                  {formatProgressText(item.message)}
                </p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {failure ? <WorkflowNotice tone="danger" title="확인이 필요한 내용" description={failure} /> : null}

      {status === 'failed' && onRetry ? (
        <PrimaryButton type="button" data-testid="diagnosis-job-retry" onClick={onRetry} disabled={isRetrying} fullWidth className="mt-2">
          {isRetrying ? <RefreshCw size={16} className="animate-spin" /> : <RotateCcw size={16} />}
          {isRetrying ? '다시 시도 중...' : '실패 단계 다시 시도'}
        </PrimaryButton>
      ) : null}
    </SectionCard>
  );
}
