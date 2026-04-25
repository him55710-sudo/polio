import React from 'react';
import { AlertTriangle, CheckCircle2, ListChecks, Wand2, Wrench } from 'lucide-react';
import { Button } from '../../../components/ui/button';
import { cn } from '../../../lib/cn';
import type { FormatValidationResult } from '../validators/reportValidation';

interface ReportValidationPanelProps {
  result: FormatValidationResult;
  className?: string;
  onRequestAiFix?: () => void;
  onEditManually?: () => void;
  onContinueAnyway?: () => void;
}

export function ReportValidationPanel({
  result,
  className,
  onRequestAiFix,
  onEditManually,
  onContinueAnyway,
}: ReportValidationPanelProps) {
  const hasErrors = result.errors.length > 0;
  const hasWarnings = result.warnings.length > 0;
  const canContinue = !hasErrors && hasWarnings;

  return (
    <section className={cn('rounded-xl border border-slate-200 bg-white p-4 shadow-sm', className)}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-black uppercase tracking-wide text-blue-600">내보내기 전 점검</p>
          <h3 className="mt-1 text-base font-black text-slate-900">
            {hasErrors ? '수정이 필요한 항목이 있어요' : hasWarnings ? '확인할 경고가 있어요' : '보고서 양식 점검 통과'}
          </h3>
          <p className="mt-1 text-sm font-medium leading-6 text-slate-600">
            표지, 로마숫자 섹션, 참고문헌, 출처, 그림, 수식을 내보내기 전에 확인합니다.
          </p>
        </div>
        {hasErrors || hasWarnings ? (
          <AlertTriangle className={hasErrors ? 'text-red-500' : 'text-amber-500'} size={22} />
        ) : (
          <CheckCircle2 className="text-emerald-600" size={22} />
        )}
      </div>

      <ValidationList title="오류" tone="danger" items={result.errors} emptyText="오류 없음" />
      <ValidationList title="경고" tone="warning" items={result.warnings} emptyText="경고 없음" />
      <ValidationList title="자동 보완 가능" tone="info" items={result.autoFixes} emptyText="자동 보완 제안 없음" />

      <div className="mt-4 flex flex-wrap gap-2">
        {(hasErrors || hasWarnings) && onRequestAiFix ? (
          <Button size="sm" variant="primary" onClick={onRequestAiFix}>
            <Wand2 size={14} />
            AI에게 보완 요청
          </Button>
        ) : null}
        {(hasErrors || hasWarnings) && onEditManually ? (
          <Button size="sm" variant="secondary" onClick={onEditManually}>
            <Wrench size={14} />
            직접 수정
          </Button>
        ) : null}
        {canContinue && onContinueAnyway ? (
          <Button size="sm" variant="ghost" onClick={onContinueAnyway}>
            그래도 내보내기
          </Button>
        ) : null}
      </div>
    </section>
  );
}

function ValidationList({
  title,
  tone,
  items,
  emptyText,
}: {
  title: string;
  tone: 'danger' | 'warning' | 'info';
  items: string[];
  emptyText: string;
}) {
  const colorClass =
    tone === 'danger'
      ? 'border-red-100 bg-red-50 text-red-800'
      : tone === 'warning'
        ? 'border-amber-100 bg-amber-50 text-amber-900'
        : 'border-blue-100 bg-blue-50 text-blue-900';

  return (
    <div className={cn('mt-3 rounded-lg border px-3 py-2 text-xs leading-5', colorClass)}>
      <p className="mb-1 inline-flex items-center gap-1.5 font-black">
        <ListChecks size={13} />
        {title}
      </p>
      {items.length ? (
        items.slice(0, 5).map((item) => <p key={item}>{item}</p>)
      ) : (
        <p className="font-medium opacity-80">{emptyText}</p>
      )}
    </div>
  );
}
