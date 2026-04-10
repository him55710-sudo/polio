import React from 'react';
import { cn } from '../../lib/cn';

interface AppShellProps {
  topbar?: React.ReactNode;
  sidebar?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  overlay?: React.ReactNode;
  className?: string;
  contentClassName?: string;
}

export function AppShell({ topbar, sidebar, children, footer, overlay, className, contentClassName }: AppShellProps) {
  return (
    <div className={cn('flex min-h-screen min-h-[100dvh] flex-col bg-[#f8fafc]', className)}>
      {topbar ?? null}
      <div className="relative flex min-h-0 flex-1">
        {sidebar ?? null}
        {overlay ?? null}
        <main className="relative z-10 flex min-w-0 flex-1 flex-col overflow-hidden">
          <div
            className={cn(
              'flex-1 overflow-x-hidden overflow-y-auto bg-[radial-gradient(circle_at_top_right,rgba(0,74,173,0.03),transparent_40%)] p-3 pb-[calc(5rem+env(safe-area-inset-bottom))] sm:p-6 sm:pb-24 md:p-8',
              contentClassName,
            )}
          >
            {children}
            {footer ?? null}
          </div>
        </main>
      </div>
    </div>
  );
}
