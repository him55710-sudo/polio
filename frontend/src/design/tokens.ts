export const typographyScale = {
  eyebrow: 'text-[11px] font-bold uppercase tracking-[0.18em]',
  titleXl: 'text-3xl font-extrabold tracking-tight sm:text-4xl',
  titleLg: 'text-2xl font-extrabold tracking-tight',
  titleMd: 'text-xl font-bold tracking-tight',
  titleSm: 'text-base font-bold tracking-tight',
  bodyLg: 'text-base font-medium leading-7',
  body: 'text-sm font-medium leading-6',
  caption: 'text-xs font-medium leading-5',
} as const;

export const spacingScale = {
  1: '0.25rem',
  2: '0.5rem',
  3: '0.75rem',
  4: '1rem',
  5: '1.25rem',
  6: '1.5rem',
  8: '2rem',
  10: '2.5rem',
  12: '3rem',
} as const;

export const radiusScale = {
  sm: '0.5rem',
  md: '0.75rem',
  lg: '1rem',
  xl: '1.25rem',
  '2xl': '1.5rem',
} as const;

export const borderScale = {
  hairline: '1px',
  default: '1px',
  strong: '1.5px',
  heavy: '2px',
} as const;

export const shadowScale = {
  xs: '0 1px 2px rgba(15, 23, 42, 0.04)',
  sm: '0 2px 8px rgba(15, 23, 42, 0.06)',
  md: '0 8px 20px rgba(15, 23, 42, 0.08)',
  lg: '0 16px 34px rgba(15, 23, 42, 0.1)',
} as const;

export const semanticColorTokens = {
  background: 'bg-slate-50',
  backgroundMuted: 'bg-slate-100',
  surface: 'bg-white',
  surfaceMuted: 'bg-slate-50',
  surfaceElevated: 'bg-white',
  border: 'border-slate-200',
  borderStrong: 'border-slate-300',
  textPrimary: 'text-slate-900',
  textSecondary: 'text-slate-700',
  textMuted: 'text-slate-500',
  brand: 'text-blue-700',
  success: 'text-emerald-700',
  warning: 'text-amber-700',
  danger: 'text-red-700',
} as const;

export const interactionStateTokens = {
  hover: 'hover:bg-slate-100',
  focus: 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 focus-visible:ring-offset-2',
  disabled: 'disabled:cursor-not-allowed disabled:opacity-50',
  loading: 'animate-pulse',
} as const;
