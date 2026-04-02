import React from 'react';
import { cn } from '../../lib/cn';

export interface TabItem<T extends string = string> {
  value: T;
  label: string;
  disabled?: boolean;
}

export interface TabsProps<T extends string = string> {
  value: T;
  items: TabItem<T>[];
  onChange: (value: T) => void;
  ariaLabel?: string;
  className?: string;
}

export function Tabs<T extends string>({ value, items, onChange, ariaLabel, className }: TabsProps<T>) {
  return (
    <div role="tablist" aria-label={ariaLabel} className={cn('inline-flex rounded-2xl border border-slate-200 bg-slate-50 p-1', className)}>
      {items.map(item => {
        const active = item.value === value;
        return (
          <button
            key={item.value}
            role="tab"
            type="button"
            aria-selected={active}
            disabled={item.disabled}
            onClick={() => onChange(item.value)}
            className={cn(
              'min-w-0 rounded-xl px-3 py-2 text-sm font-bold transition-colors',
              active ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900',
              item.disabled && 'cursor-not-allowed opacity-50',
            )}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

