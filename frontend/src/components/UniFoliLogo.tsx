import React from 'react';
import { cn } from '../lib/cn';

type LogoSize = 'sm' | 'md' | 'lg';
type LogoTone = 'light' | 'dark';

interface UniFoliLogoProps {
  size?: LogoSize;
  tone?: LogoTone;
  markOnly?: boolean;
  subtitle?: string | null;
  className?: string;
  markClassName?: string;
  titleClassName?: string;
  subtitleClassName?: string;
}

const sizeStyles: Record<
  LogoSize,
  {
    root: string;
    wordmark: string;
    mark: string;
    subtitle: string;
    panelPadding: string;
  }
> = {
  sm: {
    root: 'gap-1.5',
    wordmark: 'text-[1.75rem]',
    mark: 'h-7',
    subtitle: 'text-[10px]',
    panelPadding: 'px-2.5 py-1.5',
  },
  md: {
    root: 'gap-2',
    wordmark: 'text-[2.05rem]',
    mark: 'h-8',
    subtitle: 'text-xs',
    panelPadding: 'px-3 py-2',
  },
  lg: {
    root: 'gap-2.5',
    wordmark: 'text-[2.85rem]',
    mark: 'h-11',
    subtitle: 'text-sm',
    panelPadding: 'px-3.5 py-2.5',
  },
};

const toneStyles: Record<LogoTone, { subtitle: string; panel: string }> = {
  light: {
    subtitle: 'text-slate-500',
    panel: '',
  },
  dark: {
    subtitle: 'text-slate-300',
    panel: 'rounded-[1.25rem] bg-white/96 shadow-[0_12px_32px_rgba(15,23,42,0.16)]',
  },
};

function UniFoliMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 44 62"
      className={cn('w-auto text-[#004aad]', className)}
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      fill="none"
    >
      <path
        d="M20.6 57.5V28.2c0-8.4 3-15.4 9-20.9"
        stroke="currentColor"
        strokeWidth="4.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M17.2 24.2C10.5 23 5 17.3 4 8.7c8.2.4 14.7 4.3 18.5 10.6-0.9 3-2.8 4.7-5.3 4.9Z"
        fill="currentColor"
      />
      <path
        d="M24.2 24.6c8-1.3 14.3-7.4 15.8-18.6-8.8.1-15.8 4-20.2 11 .5 3.5 1.9 6.3 4.4 7.6Z"
        fill="currentColor"
      />
    </svg>
  );
}

function UniFoliWordmark({
  size,
  titleClassName,
}: {
  size: LogoSize;
  titleClassName?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex select-none items-end whitespace-nowrap leading-none font-[700] tracking-[-0.075em] text-[#004aad]',
        sizeStyles[size].wordmark,
        titleClassName,
      )}
    >
      <span className="sr-only">UniFoli</span>
      <span aria-hidden="true">Un</span>
      <span aria-hidden="true" className={cn('mx-[0.015em] inline-flex items-end', sizeStyles[size].mark)}>
        <UniFoliMark className="h-full" />
      </span>
      <span aria-hidden="true">Foli</span>
    </span>
  );
}

export function UniFoliLogo({
  size = 'md',
  tone = 'light',
  markOnly = false,
  subtitle = '기록 중심 입시 준비 워크플로',
  className,
  markClassName,
  titleClassName,
  subtitleClassName,
}: UniFoliLogoProps) {
  const panelClassName = toneStyles[tone].panel
    ? cn('inline-flex items-center justify-center', toneStyles[tone].panel, sizeStyles[size].panelPadding, markClassName)
    : cn('inline-flex items-center justify-center', markClassName);

  if (markOnly) {
    return (
      <span
        role="img"
        aria-label="UniFoli"
        className={cn('inline-flex items-center justify-center', className)}
      >
        <span className={panelClassName}>
          <UniFoliMark className={sizeStyles[size].mark} />
        </span>
      </span>
    );
  }

  return (
    <div className={cn('inline-flex flex-col items-start', sizeStyles[size].root, className)}>
      <span className={panelClassName}>
        <UniFoliWordmark size={size} titleClassName={titleClassName} />
      </span>
      {subtitle ? (
        <p
          className={cn(
            'font-semibold leading-none',
            sizeStyles[size].subtitle,
            toneStyles[tone].subtitle,
            subtitleClassName,
          )}
        >
          {subtitle}
        </p>
      ) : null}
    </div>
  );
}
