import React from 'react';
import { cn } from '../../lib/cn';

interface AppShellProps {
  topbar: React.ReactNode;
  sidebar: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  overlay?: React.ReactNode;
  className?: string;
}

export function AppShell({ topbar, sidebar, children, footer, overlay, className }: AppShellProps) {
  return (
    <div className={cn('flex h-screen flex-col bg-[radial-gradient(circle_at_top_right,_rgba(59,130,246,0.08),_transparent_32%),#f4f7fb]', className)}>
      {topbar}
      <div className="relative flex min-h-0 flex-1">
        {sidebar}
        {overlay}
        <main className="relative z-10 flex min-w-0 flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-auto p-5 pb-24 sm:p-7 md:p-8">
            {children}
            {footer}
          </div>
        </main>
      </div>
    </div>
  );
}
