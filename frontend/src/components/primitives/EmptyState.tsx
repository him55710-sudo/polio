import React from 'react';
import { cn } from '../../lib/cn';
import { SecondaryButton } from './SecondaryButton';

interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
  className?: string;
}

export function EmptyState({ title, description, actionLabel, onAction, icon, className }: EmptyStateProps) {
  return (
    <div className={cn('rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center', className)}>
      {icon ? <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-slate-400">{icon}</div> : null}
      <h3 className="text-lg font-bold tracking-tight text-slate-900">{title}</h3>
      <p className="mx-auto mt-2 max-w-xl text-sm font-medium leading-6 text-slate-500">{description}</p>
      {actionLabel && onAction ? (
        <div className="mt-5">
          <SecondaryButton onClick={onAction}>{actionLabel}</SecondaryButton>
        </div>
      ) : null}
    </div>
  );
}
