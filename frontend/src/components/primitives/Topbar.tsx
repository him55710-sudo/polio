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
          ? 'sticky top-0 z-40 flex items-center justify-between border-b border-white/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.88)_0%,rgba(247,249,255,0.82)_100%)] px-4 pb-3 pt-[calc(0.85rem+env(safe-area-inset-top))] shadow-[0_16px_34px_rgba(42,64,132,0.08)] backdrop-blur-2xl md:hidden'
          : 'sticky top-0 z-20 hidden items-center justify-between border-b border-white/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.82)_0%,rgba(247,249,255,0.76)_100%)] px-6 py-4 shadow-[0_14px_32px_rgba(42,64,132,0.08)] backdrop-blur-2xl md:flex',
        className,
      )}
      {...props}
    >
      {children}
    </header>
  );
}
