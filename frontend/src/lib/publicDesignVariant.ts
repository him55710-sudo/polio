export type PublicDesignVariant = 'classic' | 'portal';

export const PUBLIC_DESIGN_VARIANT_STORAGE_KEY = 'uni_foli_public_design_variant';

const variants: PublicDesignVariant[] = ['classic', 'portal'];

function normalizePublicDesignVariant(value: unknown): PublicDesignVariant {
  return variants.includes(value as PublicDesignVariant) ? (value as PublicDesignVariant) : 'classic';
}

export function getPublicDesignVariant(): PublicDesignVariant {
  if (typeof window === 'undefined') return 'classic';

  try {
    return normalizePublicDesignVariant(window.localStorage.getItem(PUBLIC_DESIGN_VARIANT_STORAGE_KEY));
  } catch {
    return 'classic';
  }
}

export function setPublicDesignVariant(variant: PublicDesignVariant) {
  if (typeof window === 'undefined') return;

  window.localStorage.setItem(PUBLIC_DESIGN_VARIANT_STORAGE_KEY, normalizePublicDesignVariant(variant));
}
