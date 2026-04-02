import React from 'react';
import { Badge, type BadgeTone } from '../ui';

type StatusVariant = 'neutral' | 'active' | 'success' | 'warning' | 'danger';

const toneMap: Record<StatusVariant, BadgeTone> = {
  neutral: 'neutral',
  active: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'danger',
};

export interface StatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status?: StatusVariant;
}

export function StatusBadge({ status = 'neutral', children, ...props }: StatusBadgeProps) {
  return (
    <Badge tone={toneMap[status]} {...props}>
      {children}
    </Badge>
  );
}

