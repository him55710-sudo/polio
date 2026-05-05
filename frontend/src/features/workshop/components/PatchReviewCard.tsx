import React, { useMemo } from 'react';
import { AlertTriangle, Check, CheckCircle2, Edit3, FileText, RotateCcw, ShieldCheck, Sparkles, X } from 'lucide-react';
import { Button } from '../../../components/ui/button';
import { cn } from '../../../lib/cn';
import type { SourceRecord } from '../types/reportDocument';
import type { FormatValidationResult } from '../validators/reportValidation';
import {
  formatPatchActionLabel,
  formatPatchPreview,
  formatPatchTargetLabel,
  getPatchSourceIds,
  normalizePatchForReview,
  summarizeValidation,
  type ReviewablePatch,
} from '../utils/messageFormatters';

interface PatchReviewCardProps {
  patch: ReviewablePatch;
  sources?: SourceRecord[];
  validation?: FormatValidationResult | null;
  className?: string;
  disabled?: boolean;
  onApply: (patch: ReviewablePatch) => void;
  onReject: (patch: ReviewablePatch) => void;
  onRequestRewrite?: (patch: ReviewablePatch, tone: 'simpler' | 'professional' | 'custom') => void;
  onEditBeforeApply?: (patch: ReviewablePatch) => void;
  onOpenProfessionalEditor?: (patch: ReviewablePatch) => void;
}

export function PatchReviewCard({
  patch,
  sources = [],
  validation,
  className,
  disabled = false,
  onApply,
  onReject,
  onRequestRewrite,
  onEditBeforeApply,
  onOpenProfessionalEditor,
}: PatchReviewCardProps) {
  const normalizedPatch = useMemo(() => normalizePatchForReview(patch), [patch]);
  const preview = useMemo(() => formatPatchPreview(patch), [patch]);
  const sourceIds = useMemo(() => getPatchSourceIds(patch), [patch]);
  const validationSummary = summarizeValidation(validation);
  const targetLabel = formatPatchTargetLabel(patch);
  const actionLabel = formatPatchActionLabel(patch);
  const applyDisabled = disabled || validationSummary.hasErrors;
  const linkedSourceCount = sources.filter((source) => sourceIds.includes(source.id)).length || sourceIds.length;

  return (
    <section
      className={cn(
        'rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm',
        validationSummary.hasErrors && 'border-red-200 bg-red-50/30',
        className,
      )}
      aria-label="문서 반영 제안"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-2 inline-flex items-center gap-2 rounded-lg bg-blue-50 px-2.5 py-1 text-xs font-black text-blue-700">
            <ShieldCheck size={14} />
            승인 후 반영
          </div>
          <h3 className="text-sm font-black text-slate-900">
            이 내용을 ‘{targetLabel}’에 반영할까요?
          </h3>
          <p className="mt-1 text-xs font-bold text-slate-500">수정 방식: {actionLabel}</p>
        </div>
        <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-[11px] font-black uppercase text-slate-600">
          {normalizedPatch.status}
        </span>
      </div>

      {preview ? (
        <div className="mt-3 max-h-44 overflow-y-auto rounded-lg border border-slate-100 bg-slate-50 p-3">
          <p className="mb-2 text-[11px] font-black uppercase tracking-wide text-slate-500">미리보기</p>
          <pre className="whitespace-pre-wrap font-sans text-xs leading-5 text-slate-700">{preview}</pre>
        </div>
      ) : null}

      <div className="mt-3 space-y-2 text-xs leading-5 text-slate-600">
        {normalizedPatch.rationale ? (
          <p>
            <span className="font-black text-slate-800">반영 이유: </span>
            {normalizedPatch.rationale}
          </p>
        ) : null}
        {normalizedPatch.type === 'content' && normalizedPatch.evidenceBoundaryNote ? (
          <p>
            <span className="font-black text-slate-800">근거 경계: </span>
            {normalizedPatch.evidenceBoundaryNote}
          </p>
        ) : null}
        {normalizedPatch.type === 'content' ? (
          <p>
            <span className="font-black text-slate-800">출처: </span>
            {linkedSourceCount > 0 ? `${linkedSourceCount}개 연결됨` : '출처 필요'}
          </p>
        ) : null}
      </div>

      <div
        className={cn(
          'mt-3 rounded-lg border px-3 py-2 text-xs font-medium leading-5',
          validationSummary.tone === 'danger' && 'border-red-200 bg-red-50 text-red-800',
          validationSummary.tone === 'warning' && 'border-amber-200 bg-amber-50 text-amber-900',
          validationSummary.tone === 'success' && 'border-emerald-200 bg-emerald-50 text-emerald-800',
        )}
      >
        <p className="mb-1 inline-flex items-center gap-1.5 font-black">
          {validationSummary.tone === 'success' ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
          {validationSummary.tone === 'danger'
            ? '적용 전 수정 필요'
            : validationSummary.tone === 'warning'
              ? '확인할 경고'
              : '검증 통과'}
        </p>
        {validationSummary.messages.slice(0, 3).map((message) => (
          <p key={message}>{message}</p>
        ))}
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <Button size="sm" variant="primary" onClick={() => onApply(patch)} disabled={applyDisabled}>
          <Check size={14} />
          문서에 반영
        </Button>
        <Button size="sm" variant="secondary" onClick={() => onRequestRewrite?.(patch, 'simpler')} disabled={disabled}>
          <RotateCcw size={14} />
          더 쉽게
        </Button>
        <Button size="sm" variant="secondary" onClick={() => onRequestRewrite?.(patch, 'professional')} disabled={disabled}>
          <Sparkles size={14} />
          더 전문적으로
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => (onEditBeforeApply ? onEditBeforeApply(patch) : onRequestRewrite?.(patch, 'custom'))}
          disabled={disabled}
        >
          <Edit3 size={14} />
          수정해서 반영
        </Button>
        {onOpenProfessionalEditor ? (
          <Button className="sm:col-span-2" size="sm" variant="secondary" onClick={() => onOpenProfessionalEditor(patch)} disabled={disabled}>
            <FileText size={14} />
            전문 편집기로 열기
          </Button>
        ) : null}
        <Button className="sm:col-span-2" size="sm" variant="ghost" onClick={() => onReject(patch)} disabled={disabled}>
          <X size={14} />
          거절
        </Button>
      </div>

      <div className="mt-3 flex items-center gap-2 text-[11px] font-medium text-slate-500">
        <FileText size={13} />
        승인하지 않은 제안은 오른쪽 문서에 적용되지 않습니다.
      </div>
    </section>
  );
}
