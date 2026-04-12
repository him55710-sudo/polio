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
    'border-transparent bg-[linear-gradient(135deg,#1d4fff_0%,#2da3ff_100%)] text-white shadow-[0_14px_28px_rgba(29,79,255,0.28)] hover:-translate-y-0.5 hover:shadow-[0_18px_34px_rgba(29,79,255,0.32)]',
  secondary: 'border-[#d6e4ff] bg-white/95 text-[#19305f] shadow-[0_8px_20px_rgba(25,69,179,0.08)] hover:bg-[#f7faff]',
  tertiary: 'border-transparent bg-[#edf4ff] text-[#1f3f86] hover:bg-[#e3eeff]',
  ghost: 'border-transparent bg-transparent text-slate-600 hover:bg-[#edf3ff] hover:text-[#15305f]',
  danger: 'border-transparent bg-red-600 text-white shadow-md shadow-red-900/15 hover:bg-red-700',
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
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1d4fff]/30 focus-visible:ring-offset-2',
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
