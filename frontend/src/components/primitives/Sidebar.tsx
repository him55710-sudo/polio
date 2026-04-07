import React from 'react';
import { cn } from '../../lib/cn';

interface SidebarProps {
  open?: boolean;
  className?: string;
  children: React.ReactNode;
}

export function Sidebar({ open, className, children }: SidebarProps) {
  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-40 bg-white border-r border-slate-200 transition-all duration-300 ease-in-out md:relative md:z-10',
        open 
          ? 'w-[280px] translate-x-0' 
          : 'w-[0px] -translate-x-full md:w-20 md:translate-x-0',
        className,
      )}
    >
      <div className={cn(
        "h-full overflow-hidden transition-opacity duration-200",
        !open && "md:opacity-100 opacity-0"
      )}>
        {children}
      </div>
    </aside>
  );
}
