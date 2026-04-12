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
        'rounded-[1.6rem] border border-[#d7e5ff] bg-white/90 backdrop-blur-sm',
        elevated ? 'shadow-[0_18px_34px_rgba(24,66,170,0.16)]' : 'shadow-[0_10px_24px_rgba(24,66,170,0.09)]',
        className,
      )}
    >
      {children}
    </Card>
  );
}
