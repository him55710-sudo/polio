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
        'group relative rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-[0_4px_20px_rgba(0,0,0,0.03)] transition-all hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)]',
        validationSummary.hasErrors && 'border-red-200 bg-red-50/20',
        className,
      )}
      aria-label="문서 반영 제안"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-3 flex items-center gap-2">
            <div className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-[10px] font-black uppercase tracking-wider text-indigo-700 ring-1 ring-indigo-200/50">
              <Sparkles size={12} />
              AI 제안
            </div>
            <div className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-[10px] font-black uppercase tracking-wider text-slate-600">
              <FileText size={12} />
              {targetLabel}
            </div>
          </div>
          <h3 className="text-[15px] font-black leading-snug text-slate-900">
            문서의 내용을 최신 분석 결과로 업데이트할까요?
          </h3>
        </div>
      </div>

      {preview ? (
        <div className="mt-4 overflow-hidden rounded-xl border border-slate-100 bg-slate-50/50">
          <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-3 py-2">
            <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">변경 내용 미리보기</span>
            <div className="flex gap-1">
              <div className="h-1.5 w-1.5 rounded-full bg-slate-200" />
              <div className="h-1.5 w-1.5 rounded-full bg-slate-200" />
            </div>
          </div>
          <div className="max-h-40 overflow-y-auto p-4">
            <pre className="whitespace-pre-wrap font-sans text-[13px] leading-6 text-slate-600">{preview}</pre>
          </div>
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

      <div className="mt-5 flex flex-col gap-2">
        <Button
          size="lg"
          variant="primary"
          onClick={() => onApply(patch)}
          disabled={applyDisabled}
          className="w-full bg-indigo-600 py-6 text-sm font-black shadow-lg shadow-indigo-200 transition-all hover:bg-indigo-700 hover:scale-[1.01] active:scale-95"
        >
          <Check size={18} className="mr-2" />
          변경 사항 승인 및 적용
        </Button>

        <div className="grid grid-cols-2 gap-2">
          <Button size="sm" variant="secondary" onClick={() => onRequestRewrite?.(patch, 'simpler')} disabled={disabled} className="h-10 border-slate-200 bg-white font-bold text-slate-700 hover:bg-slate-50">
            <RotateCcw size={14} className="mr-2" />
            더 쉽게
          </Button>
          <Button size="sm" variant="secondary" onClick={() => onRequestRewrite?.(patch, 'professional')} disabled={disabled} className="h-10 border-slate-200 bg-white font-bold text-slate-700 hover:bg-slate-50">
            <Sparkles size={14} className="mr-2" />
            더 전문적으로
          </Button>
        </div>

        <Button
          size="sm"
          variant="ghost"
          onClick={() => (onEditBeforeApply ? onEditBeforeApply(patch) : onRequestRewrite?.(patch, 'custom'))}
          disabled={disabled}
          className="h-10 font-bold text-slate-500 hover:text-indigo-600"
        >
          <Edit3 size={14} className="mr-2" />
          직접 수정해서 반영하기
        </Button>

        <div className="mt-2 flex items-center justify-between border-t border-slate-100 pt-3">
          <button onClick={() => onReject(patch)} disabled={disabled} className="text-xs font-bold text-slate-400 hover:text-red-500 transition-colors">
            거절하기
          </button>
          {onOpenProfessionalEditor && (
            <button onClick={() => onOpenProfessionalEditor(patch)} disabled={disabled} className="text-xs font-bold text-indigo-600 hover:underline">
              전문 에디터에서 열기
            </button>
          )}
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2 text-[11px] font-medium text-slate-500">
        <FileText size={13} />
        승인하지 않은 제안은 오른쪽 문서에 적용되지 않습니다.
      </div>
    </section>
  );
}
