import React from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Card } from '../ui';
import { cn } from '../../lib/cn';

interface SectionCardProps extends React.HTMLAttributes<HTMLElement> {
  title?: string;
  description?: string;
  subtitle?: string; // Alias for description
  eyebrow?: string;
  badge?: string; // New prop
  actions?: React.ReactNode;
  bodyClassName?: string;
  collapsible?: boolean;
  collapsed?: boolean;
  defaultCollapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export function SectionCard({
  title,
  description,
  subtitle,
  eyebrow,
  badge,
  actions,
  className,
  bodyClassName,
  collapsible = false,
  collapsed,
  defaultCollapsed = false,
  onCollapsedChange,
  children,
  ...props
}: SectionCardProps) {
  const isControlled = typeof collapsed === 'boolean';
  const [internalCollapsed, setInternalCollapsed] = React.useState(defaultCollapsed);
  const isCollapsed = isControlled ? Boolean(collapsed) : internalCollapsed;

  const setCollapsedState = (nextValue: boolean) => {
    if (!isControlled) {
      setInternalCollapsed(nextValue);
    }
    onCollapsedChange?.(nextValue);
  };

  const handleToggleCollapsed = () => {
    if (!collapsible) return;
    setCollapsedState(!isCollapsed);
  };

  const headerActions = (
    <>
      {actions}
      {collapsible ? (
        <button
          type="button"
          aria-label={isCollapsed ? '섹션 펼치기' : '섹션 접기'}
          aria-expanded={!isCollapsed}
          onClick={handleToggleCollapsed}
          className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[#d6e4ff] bg-white text-[#476192] transition-colors hover:bg-[#f4f8ff] hover:text-[#23458f]"
        >
          {isCollapsed ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
        </button>
      ) : null}
    </>
  );

  return (
    <Card className={cn('flex flex-col rounded-[1.75rem] border border-[#d6e4ff] bg-white/92 shadow-[0_12px_28px_rgba(24,66,170,0.1)]', className)} {...props}>
      {(title || description || eyebrow || actions || collapsible) ? (
        <header className="mb-4 flex shrink-0 flex-col gap-3 sm:mb-5 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3">
              {eyebrow ? <p className="text-xs font-black uppercase tracking-[0.18em] text-[#6980ad]">{eyebrow}</p> : null}
              {badge ? (
                <span className="inline-flex items-center rounded-full bg-[#eaf2ff] px-2.5 py-0.5 text-[10px] font-black text-[#2350b8] ring-1 ring-inset ring-[#2350b8]/15">
                  {badge}
                </span>
              ) : null}
            </div>
            {title ? <h2 className="mt-1 text-xl font-black tracking-tight text-slate-900 sm:text-2xl">{title}</h2> : null}
            {(description || subtitle) ? (
              <p className="mt-2 text-sm font-medium leading-6 text-slate-500 sm:text-base sm:leading-7">
                {description || subtitle}
              </p>
            ) : null}
          </div>
          {actions || collapsible ? (
            <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:shrink-0 sm:justify-end">{headerActions}</div>
          ) : null}
        </header>
      ) : null}
      {!isCollapsed ? <div className={cn('min-h-0 flex-1 space-y-5', bodyClassName)}>{children}</div> : null}
    </Card>
  );
}
