import React from 'react';
import { cn } from '../../lib/cn';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  containerClassName?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, hint, error, className, containerClassName, id, ...props },
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
      <input
        ref={ref}
        id={id}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy}
        className={cn(
          'h-12 w-full rounded-2xl border bg-white px-4 text-base font-medium text-slate-700 transition-colors outline-none',
          'placeholder:text-slate-400 focus-visible:ring-2 focus-visible:ring-[#004aad]/30',
          error ? 'border-red-300 focus-visible:border-red-400 focus-visible:ring-red-200' : 'border-slate-300 hover:border-slate-400',
          className,
        )}
        {...props}
      />
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

export interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
  containerClassName?: string;
}

export const TextArea = React.forwardRef<HTMLTextAreaElement, TextAreaProps>(function TextArea(
  { label, hint, error, className, containerClassName, id, rows = 5, ...props },
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
      <textarea
        ref={ref}
        id={id}
        rows={rows}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy}
        className={cn(
          'w-full rounded-2xl border bg-white px-4 py-3.5 text-base font-medium text-slate-700 transition-colors outline-none',
          'placeholder:text-slate-400 focus-visible:ring-2 focus-visible:ring-[#004aad]/30',
          error ? 'border-red-300 focus-visible:border-red-400 focus-visible:ring-red-200' : 'border-slate-300 hover:border-slate-400',
          className,
        )}
        {...props}
      />
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
