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
          className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/70 bg-white/82 text-[#476192] shadow-[0_10px_24px_rgba(42,64,132,0.08)] transition-colors hover:bg-[#f5f8ff] hover:text-[#23458f]"
        >
          {isCollapsed ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
        </button>
      ) : null}
    </>
  );

  return (
    <Card className={cn('flex flex-col rounded-[2rem] border border-white/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.92)_0%,rgba(245,248,255,0.88)_100%)] shadow-[0_18px_40px_rgba(42,64,132,0.1)] backdrop-blur-xl', className)} {...props}>
      {(title || description || eyebrow || actions || collapsible) ? (
        <header className="mb-5 flex shrink-0 flex-col gap-4 sm:mb-6 sm:flex-row sm:items-start sm:justify-between sm:gap-5">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2.5">
              {eyebrow ? <p className="text-[11px] font-black uppercase tracking-[0.2em] text-[#6278aa]">{eyebrow}</p> : null}
              {badge ? (
                <span className="inline-flex items-center rounded-full bg-[linear-gradient(135deg,#ecf1ff_0%,#eefaff_100%)] px-3 py-1 text-[10px] font-black text-[#2350b8] ring-1 ring-inset ring-[#2350b8]/12">
                  {badge}
                </span>
              ) : null}
            </div>
            {title ? <h2 className="mt-1.5 text-xl font-black tracking-tight text-slate-900 sm:text-[1.7rem]">{title}</h2> : null}
            {(description || subtitle) ? (
              <p className="mt-2.5 max-w-3xl text-sm font-medium leading-6 text-slate-500 sm:text-base sm:leading-7">
                {description || subtitle}
              </p>
            ) : null}
          </div>
          {actions || collapsible ? (
            <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:shrink-0 sm:justify-end">{headerActions}</div>
          ) : null}
        </header>
      ) : null}
      {!isCollapsed ? <div className={cn('min-h-0 flex-1 space-y-6', bodyClassName)}>{children}</div> : null}
    </Card>
  );
}
