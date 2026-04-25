import React from 'react';
import { MessageSquare, ScrollText } from 'lucide-react';
import { cn } from '../../../lib/cn';

interface WorkshopMobileToggleProps {
  value: 'chat' | 'draft';
  onChange: (value: 'chat' | 'draft') => void;
  className?: string;
}

export function WorkshopMobileToggle({ value, onChange, className }: WorkshopMobileToggleProps) {
  return (
    <div className={cn('inline-flex w-full items-center gap-1 rounded-2xl border border-slate-200 bg-white p-1 shadow-sm', className)}>
      <button
        type="button"
        onClick={() => onChange('chat')}
        className={cn(
          'inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-xl px-3 text-sm font-black transition-all',
          value === 'chat' ? 'bg-[#3182f6] text-white shadow-md shadow-blue-100' : 'text-slate-600 hover:bg-slate-50',
        )}
      >
        <MessageSquare size={15} />
        채팅
      </button>
      <button
        type="button"
        onClick={() => onChange('draft')}
        className={cn(
          'inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-xl px-3 text-sm font-black transition-all',
          value === 'draft' ? 'bg-[#3182f6] text-white shadow-md shadow-blue-100' : 'text-slate-600 hover:bg-slate-50',
        )}
      >
        <ScrollText size={15} />
        문서
      </button>
    </div>
  );
}
