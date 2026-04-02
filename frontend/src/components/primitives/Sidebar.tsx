import React from 'react';
import { cn } from '../../lib/cn';

interface SidebarProps extends React.HTMLAttributes<HTMLElement> {
  open: boolean;
}

export function Sidebar({ open, className, children, ...props }: SidebarProps) {
  return (
    <aside
      className={cn(
        'absolute inset-y-0 left-0 z-30 flex h-full flex-col border-r border-slate-200 bg-white transition-all duration-200 md:relative',
        open ? 'w-80 translate-x-0' : 'w-20 -translate-x-full md:translate-x-0',
        className,
      )}
      {...props}
    >
      {children}
    </aside>
  );
}
