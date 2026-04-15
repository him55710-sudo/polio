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
    <div className={cn('flex min-h-screen min-h-[100dvh] flex-col bg-[linear-gradient(180deg,#fafcff_0%,#f3f6ff_48%,#f8f4ff_100%)]', className)}>
      {topbar ?? null}
      <div className="relative flex min-h-0 flex-1">
        {sidebar ?? null}
        {overlay ?? null}
        <main className="relative z-10 flex min-w-0 flex-1 flex-col overflow-hidden">
          <div
            className={cn(
              'flex-1 overflow-x-hidden overflow-y-auto bg-[radial-gradient(circle_at_0%_0%,rgba(56,189,248,0.16),transparent_22%),radial-gradient(circle_at_92%_0%,rgba(99,102,241,0.14),transparent_26%),radial-gradient(circle_at_50%_100%,rgba(251,113,133,0.08),transparent_24%),linear-gradient(180deg,#fbfcff_0%,#f4f7ff_45%,#fbf7ff_100%)] px-3 py-4 pb-[calc(5rem+env(safe-area-inset-bottom))] sm:px-6 sm:py-6 sm:pb-24 md:px-8 md:py-8',
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
