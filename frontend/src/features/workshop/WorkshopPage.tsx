import React from 'react';
import { cn } from '../../lib/cn';
import { WorkshopChatPanel } from './components/WorkshopChatPanel';
import { WorkshopEditorPanel } from './components/WorkshopEditorPanel';
import { WorkshopMobileToggle } from './components/WorkshopMobileToggle';

interface WorkshopPageProps {
  chat?: React.ReactNode;
  editor?: React.ReactNode;
  mobileView?: 'chat' | 'draft';
  onMobileViewChange?: (value: 'chat' | 'draft') => void;
  className?: string;
}

export function WorkshopPage({
  chat,
  editor,
  mobileView = 'chat',
  onMobileViewChange,
  className,
}: WorkshopPageProps) {
  return (
    <main className={cn('mx-auto max-w-[1800px] px-2.5 py-3 sm:px-4 sm:py-6', className)}>
      {onMobileViewChange ? (
        <div className="mb-4 lg:hidden">
          <WorkshopMobileToggle value={mobileView} onChange={onMobileViewChange} />
        </div>
      ) : null}
      <div className="grid gap-6 lg:grid-cols-[400px_minmax(0,1fr)] xl:grid-cols-[460px_minmax(0,1fr)]">
        <WorkshopChatPanel className={cn(mobileView !== 'chat' && 'hidden lg:flex')}>{chat}</WorkshopChatPanel>
        <WorkshopEditorPanel className={cn(mobileView !== 'draft' && 'hidden lg:flex')}>{editor}</WorkshopEditorPanel>
      </div>
    </main>
  );
}
