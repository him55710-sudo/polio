import React from 'react';
import { Badge } from '../ui';

interface WorkflowContextHeaderProps {
  sectionLabel: string;
  summary: string;
}

export function WorkflowContextHeader({ sectionLabel, summary }: WorkflowContextHeaderProps) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-2.5">
        <Badge tone="info">현재 섹션</Badge>
        <h1 className="text-base font-black text-slate-800">{sectionLabel}</h1>
      </div>
      <p className="mt-1.5 max-w-3xl truncate text-[13px] font-medium text-slate-500">{summary}</p>
    </div>
  );
}
