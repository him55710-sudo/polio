import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { cn } from '../../lib/cn';

type DialogSize = 'sm' | 'md' | 'lg';

const sizeClass: Record<DialogSize, string> = {
  sm: 'max-w-md',
  md: 'max-w-xl',
  lg: 'max-w-2xl',
};

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  className?: string;
}

export function Dialog({ open, onClose, children, className }: DialogProps) {
  useEffect(() => {
    if (!open) return undefined;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKeyDown);

    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="대화상자 닫기"
        onClick={onClose}
        className="absolute inset-0 bg-slate-900/45 backdrop-blur-[2px]"
      />
      <div className={cn('relative w-full overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-2xl', className)}>
        {children}
      </div>
    </div>
  );
}

export interface DialogPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: DialogSize;
}

export function DialogPanel({ size = 'md', className, ...props }: DialogPanelProps) {
  return <div className={cn('mx-auto w-full', sizeClass[size], className)} {...props} />;
}

export interface DialogHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: string;
  onClose?: () => void;
}

export function DialogHeader({ title, description, onClose, className, ...props }: DialogHeaderProps) {
  return (
    <header className={cn('border-b border-slate-100 px-6 py-5', className)} {...props}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold tracking-tight text-slate-900">{title}</h2>
          {description ? <p className="mt-1 text-sm font-medium leading-6 text-slate-500">{description}</p> : null}
        </div>
        {onClose ? (
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
            aria-label="대화상자 닫기"
          >
            <X size={18} />
          </button>
        ) : null}
      </div>
    </header>
  );
}

export function DialogBody({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('px-6 py-5', className)} {...props} />;
}

export function DialogFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <footer className={cn('flex flex-wrap items-center justify-end gap-3 border-t border-slate-100 px-6 py-4', className)} {...props} />;
}
