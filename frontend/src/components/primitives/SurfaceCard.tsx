import React from 'react';
import { cn } from '../../lib/cn';
import { Card, type CardProps } from '../ui';

interface SurfaceCardProps extends CardProps {
  elevated?: boolean;
}

export function SurfaceCard({ elevated = false, className, children, ...props }: SurfaceCardProps) {
  return (
    <Card
      {...props}
      className={cn(
        'rounded-2xl border border-slate-200 bg-white',
        elevated ? 'shadow-md' : 'shadow-sm',
        className,
      )}
    >
      {children}
    </Card>
  );
}
