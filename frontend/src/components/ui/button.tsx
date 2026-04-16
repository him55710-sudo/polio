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
  primary:
    'border-indigo-400/20 bg-gradient-to-br from-indigo-500 via-indigo-600 to-purple-600 text-white shadow-xl shadow-indigo-200/50 hover:-translate-y-0.5 hover:shadow-2xl hover:shadow-indigo-300/60 active:scale-[0.98]',
  secondary:
    'border-slate-200 bg-white text-slate-700 shadow-sm hover:border-indigo-200 hover:bg-slate-50 hover:text-indigo-700 active:scale-[0.98]',
  tertiary: 'border-transparent bg-indigo-50 text-indigo-700 hover:bg-indigo-100',
  ghost: 'border-transparent bg-transparent text-slate-500 hover:bg-slate-100 hover:text-indigo-600',
  danger: 'border-transparent bg-rose-600 text-white shadow-lg shadow-rose-100 hover:bg-rose-700 active:scale-[0.98]',
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-10 rounded-[0.9rem] px-3.5 text-sm font-bold',
  md: 'h-12 rounded-[1.1rem] px-5 text-sm font-bold',
  lg: 'h-14 rounded-[1.2rem] px-6 text-base font-black',
  icon: 'h-12 w-12 rounded-[1.1rem] p-0',
};

export function buttonClassName(options: ButtonStyleOptions = {}) {
  const { variant = 'secondary', size = 'md', fullWidth = false } = options;

  return cn(
    'inline-flex items-center justify-center gap-2 border transition-all duration-200 ease-out disabled:cursor-not-allowed disabled:opacity-50',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600/30 focus-visible:ring-offset-2',
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
