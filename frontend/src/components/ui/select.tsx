import React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '../../lib/cn';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  label?: string;
  hint?: string;
  error?: string;
  options: SelectOption[];
  containerClassName?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, hint, error, options, className, containerClassName, id, ...props },
  ref,
) {
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;

  return (
    <div className={cn('space-y-2', containerClassName)}>
      {label ? (
        <label htmlFor={id} className="block text-sm font-bold text-slate-700">
          {label}
        </label>
      ) : null}

      <div className="relative">
        <select
          ref={ref}
          id={id}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy}
          className={cn(
            'h-11 w-full appearance-none rounded-2xl border bg-white px-3.5 pr-10 text-sm font-medium text-slate-700 outline-none transition-colors',
            'focus-visible:ring-2 focus-visible:ring-blue-300',
            error ? 'border-red-300 focus-visible:ring-red-200' : 'border-slate-300 hover:border-slate-400',
            className,
          )}
          {...props}
        >
          {options.map(option => (
            <option key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown size={16} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" />
      </div>

      {hint && !error ? (
        <p id={`${id}-hint`} className="text-xs font-medium text-slate-500">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${id}-error`} className="text-xs font-semibold text-red-600">
          {error}
        </p>
      ) : null}
    </div>
  );
});
