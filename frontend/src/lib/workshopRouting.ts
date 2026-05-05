import { DIAGNOSIS_STORAGE_KEY } from './diagnosis';

const INVALID_PROJECT_IDS = new Set(['', 'demo', 'undefined', 'null']);

export function normalizeWorkshopProjectId(value: string | null | undefined): string | null {
  const normalized = String(value ?? '').trim();
  if (!normalized || INVALID_PROJECT_IDS.has(normalized.toLowerCase())) return null;
  return normalized;
}

export function readStoredWorkshopProjectId(storage: Storage | null = getBrowserStorage()): string | null {
  if (!storage) return null;
  try {
    const raw = storage.getItem(DIAGNOSIS_STORAGE_KEY);
    if (!raw) return null;
    const stored = JSON.parse(raw) as { projectId?: unknown };
    return normalizeWorkshopProjectId(typeof stored.projectId === 'string' ? stored.projectId : null);
  } catch {
    return null;
  }
}

export function clearStoredWorkshopProjectReference(
  projectId: string | null | undefined,
  storage: Storage | null = getBrowserStorage(),
): boolean {
  if (!storage) return false;
  const targetProjectId = normalizeWorkshopProjectId(projectId);
  try {
    const raw = storage.getItem(DIAGNOSIS_STORAGE_KEY);
    if (!raw) return false;
    const stored = JSON.parse(raw) as Record<string, unknown>;
    const storedProjectId = normalizeWorkshopProjectId(typeof stored.projectId === 'string' ? stored.projectId : null);
    if (!storedProjectId || (targetProjectId && storedProjectId !== targetProjectId)) return false;

    const next = { ...stored };
    delete next.projectId;
    storage.setItem(DIAGNOSIS_STORAGE_KEY, JSON.stringify(next));
    return true;
  } catch {
    return false;
  }
}

function getBrowserStorage(): Storage | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage;
}
