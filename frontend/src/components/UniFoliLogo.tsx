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

const sizeStyles: Record<LogoSize, { container: string; img: string; title: string; subtitle: string }> = {
  sm: {
    container: 'h-8',
    img: 'h-8',
    title: 'text-base',
    subtitle: 'text-[10px]',
  },
  md: {
    container: 'h-10',
    img: 'h-10',
    title: 'text-lg',
    subtitle: 'text-xs',
  },
  lg: {
    container: 'h-14',
    img: 'h-14',
    title: 'text-2xl',
    subtitle: 'text-sm',
  },
};

const toneStyles: Record<LogoTone, { title: string; subtitle: string }> = {
  light: {
    title: 'text-[#004aad]',
    subtitle: 'text-slate-500',
  },
  dark: {
    title: 'text-white',
    subtitle: 'text-slate-300',
  },
};

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
  // If we only want the mark, we'll use a version that extracts just the leaf part if possible, 
  // but for now we'll use a cropped/masked version or simply the full logo for consistency.
  if (markOnly) {
    return (
      <div className={cn('flex items-center justify-center overflow-hidden', sizeStyles[size].container, markClassName)}>
        <img 
          src="/logo-unifoli.png" 
          alt="Uni Foli Logo" 
          className={cn('object-contain', sizeStyles[size].img)} 
        />
      </div>
    );
  }

  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <div className={cn('flex items-center justify-center', sizeStyles[size].container, markClassName)}>
        <img 
          src="/logo-unifoli.png" 
          alt="Uni Foli Logo" 
          className={cn('object-contain', sizeStyles[size].img, tone === 'dark' && 'brightness-0 invert')} 
        />
      </div>
      <div className="flex flex-col justify-center">
        <p className={cn('font-bold tracking-tight leading-none', sizeStyles[size].title, toneStyles[tone].title, titleClassName)}>
          Uni Foli
        </p>
        {subtitle ? (
          <p
            className={cn(
              'mt-1 font-semibold opacity-90',
              sizeStyles[size].subtitle,
              toneStyles[tone].subtitle,
              subtitleClassName,
            )}
          >
            {subtitle}
          </p>
        ) : null}
      </div>
    </div>
  );
}
