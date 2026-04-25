import React from 'react';
import { Download, Save } from 'lucide-react';
import type { JSONContent } from '@tiptap/react';
import type { TiptapEditorHandle } from '../../../components/editor/TiptapEditor';
import { TiptapEditor } from '../../../components/editor/TiptapEditor';
import { Button } from '../../../components/ui/button';
import { cn } from '../../../lib/cn';
import type { ReportFormatProfile } from '../types/reportDocument';
import type { FormatValidationResult } from '../validators/reportValidation';

interface WorkshopEditorPanelProps {
  editorRef?: React.Ref<TiptapEditorHandle>;
  initialContent?: JSONContent | string | null;
  onUpdate?: (json: JSONContent, html: string, text: string) => void;
  onJsonUpdate?: (json: JSONContent) => void;
  onManualSave?: () => void | Promise<void>;
  onExportMarkdown?: () => void;
  isSaving?: boolean;
  lastSaved?: string | null;
  documentTitle?: string;
  formatProfile?: ReportFormatProfile | null;
  pendingPatchCount?: number;
  validationSummary?: FormatValidationResult | null;
  statusNotice?: React.ReactNode;
  advancedTools?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}

export function WorkshopEditorPanel({
  editorRef,
  initialContent,
  onUpdate,
  onJsonUpdate,
  onManualSave,
  onExportMarkdown,
  isSaving = false,
  lastSaved,
  documentTitle = '탐구보고서',
  formatProfile,
  pendingPatchCount = 0,
  validationSummary,
  statusNotice,
  advancedTools,
  children,
  className,
}: WorkshopEditorPanelProps) {
  if (children) {
    return <section className={cn('flex min-h-0 flex-col overflow-hidden bg-slate-50', className)}>{children}</section>;
  }

  return (
    <section className={cn('flex h-full min-h-0 flex-col overflow-hidden bg-slate-50/70', className)}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3">
        <div className="min-w-0">
          <p className="text-xs font-black uppercase tracking-wide text-indigo-500">문서 편집기</p>
          <h2 className="truncate text-base font-black text-slate-900">{documentTitle}</h2>
          <p className="mt-0.5 text-xs font-medium text-slate-500">
            {formatProfile?.templateId || 'standard_research'} · 대기 중인 제안 {pendingPatchCount}개
            {lastSaved ? ` · 마지막 저장 ${lastSaved}` : ''}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="primary" onClick={() => void onManualSave?.()} disabled={isSaving}>
            <Save size={14} />
            저장
          </Button>
          <Button size="sm" variant="secondary" onClick={onExportMarkdown}>
            <Download size={14} />
            내보내기
          </Button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden p-4 sm:p-6">
        {statusNotice}
        {validationSummary && (validationSummary.errors.length > 0 || validationSummary.warnings.length > 0) ? (
          <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-900">
            {[...validationSummary.errors, ...validationSummary.warnings].slice(0, 2).map((message) => (
              <p key={message}>{message}</p>
            ))}
          </div>
        ) : null}
        <div className="flex-1 overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-sm ring-1 ring-slate-200/50 transition-all focus-within:ring-indigo-500/30">
          <TiptapEditor
            ref={editorRef}
            initialContent={initialContent}
            onUpdate={onUpdate}
            onJsonUpdate={onJsonUpdate}
          />
        </div>
        {advancedTools}
      </div>
    </section>
  );
}
