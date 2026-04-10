import React from 'react';
import { cn } from '../../lib/cn';

export type BadgeTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

const badgeToneClass: Record<BadgeTone, string> = {
  neutral: 'border-slate-200 bg-slate-50 text-slate-600',
  info: 'border-[#004aad]/10 bg-[#004aad]/5 text-[#004aad]',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  warning: 'border-amber-200 bg-amber-50 text-amber-700',
  danger: 'border-red-200 bg-red-50 text-red-700',
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

export function Badge({ tone = 'neutral', className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-bold tracking-tight',
        badgeToneClass[tone],
        className,
      )}
      {...props}
    />
  );
}

