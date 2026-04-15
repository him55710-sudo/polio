import React from 'react';
import { cn } from '../../lib/cn';

export interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  evidence?: React.ReactNode;
  className?: string;
}

export function PageHeader({ eyebrow, title, description, actions, evidence, className }: PageHeaderProps) {
  return (
    <header className={cn('relative overflow-hidden rounded-[2rem] border border-white/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.9)_0%,rgba(246,249,255,0.84)_100%)] p-6 shadow-[0_18px_40px_rgba(42,64,132,0.1)] backdrop-blur-xl sm:p-9', className)}>
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-[radial-gradient(circle_at_12%_10%,rgba(56,189,248,0.2),transparent_32%),radial-gradient(circle_at_88%_0%,rgba(251,191,36,0.16),transparent_26%)]" />
      <div className="relative flex flex-col gap-5 sm:gap-6 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          {eyebrow ? (
            <p className="text-[11px] font-black uppercase tracking-[0.22em] text-[#335fd3]">{eyebrow}</p>
          ) : null}
          <h1 className="mt-2.5 break-keep text-2xl font-black tracking-tight text-slate-900 sm:text-4xl">{title}</h1>
          {description ? <p className="mt-3.5 max-w-3xl text-sm font-medium leading-6 text-slate-500 sm:text-base sm:leading-7">{description}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2.5">{actions}</div> : null}
      </div>
      {evidence ? <div className="relative mt-6 border-t border-white/80 pt-6">{evidence}</div> : null}
    </header>
  );
}
