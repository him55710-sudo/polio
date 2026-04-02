import React from 'react';
import { AlertTriangle, CheckCircle2, Info, Loader2 } from 'lucide-react';
import { cn } from '../../lib/cn';

type WorkflowNoticeTone = 'info' | 'success' | 'warning' | 'danger' | 'loading';

interface WorkflowNoticeProps {
  tone?: WorkflowNoticeTone;
  title: string;
  description?: string;
  className?: string;
}

function toneClass(tone: WorkflowNoticeTone) {
  if (tone === 'success') return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  if (tone === 'warning') return 'border-amber-200 bg-amber-50 text-amber-800';
  if (tone === 'danger') return 'border-red-200 bg-red-50 text-red-800';
  if (tone === 'loading') return 'border-blue-200 bg-blue-50 text-blue-800';
  return 'border-slate-200 bg-slate-50 text-slate-700';
}

function toneIcon(tone: WorkflowNoticeTone) {
  if (tone === 'success') return <CheckCircle2 size={16} />;
  if (tone === 'warning') return <AlertTriangle size={16} />;
  if (tone === 'danger') return <AlertTriangle size={16} />;
  if (tone === 'loading') return <Loader2 size={16} className="animate-spin" />;
  return <Info size={16} />;
}

export function WorkflowNotice({ tone = 'info', title, description, className }: WorkflowNoticeProps) {
  return (
    <div className={cn('rounded-2xl border px-4 py-3', toneClass(tone), className)}>
      <p className="inline-flex items-center gap-2 text-sm font-bold">
        {toneIcon(tone)}
        {title}
      </p>
      {description ? <p className="mt-1 text-sm font-medium leading-6">{description}</p> : null}
    </div>
  );
}
