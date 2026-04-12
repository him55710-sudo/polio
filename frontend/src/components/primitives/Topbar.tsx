import React from 'react';
import { cn } from '../../lib/cn';

interface TopbarProps extends React.HTMLAttributes<HTMLElement> {
  mobile?: boolean;
}

export function Topbar({ mobile = false, className, children, ...props }: TopbarProps) {
  return (
    <header
      className={cn(
        mobile
          ? 'sticky top-0 z-40 flex items-center justify-between border-b border-[#d6e4ff] bg-white/88 px-4 pb-3 pt-[calc(0.75rem+env(safe-area-inset-top))] shadow-[0_10px_24px_rgba(24,66,170,0.08)] backdrop-blur-xl md:hidden'
          : 'sticky top-0 z-20 hidden items-center justify-between border-b border-[#d6e4ff] bg-white/80 px-6 py-4 shadow-[0_10px_24px_rgba(24,66,170,0.08)] backdrop-blur-xl md:flex',
        className,
      )}
      {...props}
    >
      {children}
    </header>
  );
}
