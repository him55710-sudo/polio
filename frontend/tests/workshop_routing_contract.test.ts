import assert from 'node:assert/strict';
import test from 'node:test';

import { DIAGNOSIS_STORAGE_KEY } from '../src/lib/diagnosis';
import {
  clearStoredWorkshopProjectReference,
  normalizeWorkshopProjectId,
  readStoredWorkshopProjectId,
} from '../src/lib/workshopRouting';

class MemoryStorage implements Storage {
  private values = new Map<string, string>();

  get length() {
    return this.values.size;
  }

  clear(): void {
    this.values.clear();
  }

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  key(index: number): string | null {
    return Array.from(this.values.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.values.delete(key);
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }
}

test('normalizeWorkshopProjectId rejects placeholder route params', () => {
  assert.equal(normalizeWorkshopProjectId(undefined), null);
  assert.equal(normalizeWorkshopProjectId(''), null);
  assert.equal(normalizeWorkshopProjectId('demo'), null);
  assert.equal(normalizeWorkshopProjectId('undefined'), null);
  assert.equal(normalizeWorkshopProjectId(' null '), null);
  assert.equal(normalizeWorkshopProjectId('project-123'), 'project-123');
});

test('readStoredWorkshopProjectId ignores stale placeholder values', () => {
  const storage = new MemoryStorage();
  storage.setItem(DIAGNOSIS_STORAGE_KEY, JSON.stringify({ projectId: 'undefined', diagnosis: { headline: 'cached' } }));

  assert.equal(readStoredWorkshopProjectId(storage), null);
});

test('clearStoredWorkshopProjectReference removes only the stale project link', () => {
  const storage = new MemoryStorage();
  storage.setItem(
    DIAGNOSIS_STORAGE_KEY,
    JSON.stringify({
      projectId: 'project-123',
      targetMajor: '컴퓨터공학과',
      diagnosis: { headline: 'cached diagnosis' },
    }),
  );

  assert.equal(clearStoredWorkshopProjectReference('project-123', storage), true);

  const stored = JSON.parse(storage.getItem(DIAGNOSIS_STORAGE_KEY) || '{}') as Record<string, unknown>;
  assert.equal(stored.projectId, undefined);
  assert.equal(stored.targetMajor, '컴퓨터공학과');
  assert.deepEqual(stored.diagnosis, { headline: 'cached diagnosis' });
});

test('clearStoredWorkshopProjectReference keeps other project links intact', () => {
  const storage = new MemoryStorage();
  storage.setItem(DIAGNOSIS_STORAGE_KEY, JSON.stringify({ projectId: 'project-abc' }));

  assert.equal(clearStoredWorkshopProjectReference('project-xyz', storage), false);
  assert.equal(readStoredWorkshopProjectId(storage), 'project-abc');
});
