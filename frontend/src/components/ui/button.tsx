import React from 'react';
import { cn } from '../../lib/cn';

export type ButtonVariant = 'primary' | 'secondary' | 'tertiary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg' | 'icon';

interface ButtonStyleOptions {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: 'border-transparent bg-blue-600 text-white shadow-md shadow-blue-900/15 hover:bg-blue-700',
  secondary: 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50',
  tertiary: 'border-transparent bg-slate-100 text-slate-700 hover:bg-slate-200',
  ghost: 'border-transparent bg-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900',
  danger: 'border-transparent bg-red-600 text-white shadow-md shadow-red-900/15 hover:bg-red-700',
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-10 rounded-xl px-3.5 text-sm font-bold',
  md: 'h-12 rounded-2xl px-5 text-sm font-bold',
  lg: 'h-14 rounded-2xl px-6 text-base font-black',
  icon: 'h-12 w-12 rounded-2xl p-0',
};

export function buttonClassName(options: ButtonStyleOptions = {}) {
  const { variant = 'secondary', size = 'md', fullWidth = false } = options;

  return cn(
    'inline-flex items-center justify-center gap-2 border transition-all duration-150 ease-out disabled:cursor-not-allowed disabled:opacity-50',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 focus-visible:ring-offset-2',
    variantClasses[variant],
    sizeClasses[size],
    fullWidth && 'w-full',
  );
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, ButtonStyleOptions {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'secondary', size = 'md', fullWidth = false, className, type = 'button', ...props },
  ref,
) {
  return <button ref={ref} type={type} className={cn(buttonClassName({ variant, size, fullWidth }), className)} {...props} />;
});
