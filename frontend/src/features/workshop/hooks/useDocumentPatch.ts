import { useCallback, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import type { WorkshopDraftPatchProposal, WorkshopStructuredDraftState } from '../../../lib/workshopCoauthoring';
import type { EditorAdapter } from '../adapters/EditorAdapter';
import {
  applyReportPatchToStructuredDraft,
  convertWorkshopDraftPatchToReportPatch,
  structuredDraftToReportDocumentState,
} from '../adapters/workshopPatchAdapter';
import {
  createInitialReportDocumentState,
  type ReportDocumentState,
  type ReportPatch,
} from '../types/reportDocument';
import { isReportPatch } from '../utils/messageFormatters';
import { validateReportPatch, type FormatValidationResult } from '../validators/reportValidation';

export type RawWorkshopPatch = ReportPatch | WorkshopDraftPatchProposal;
export type PatchRewriteStyle = 'simpler' | 'professional' | 'custom';

export interface UseDocumentPatchOptions {
  getEditorAdapter?: () => EditorAdapter | null;
  structuredDraft?: WorkshopStructuredDraftState | null;
  onStructuredDraftChange?: (next: WorkshopStructuredDraftState) => void;
  documentState?: ReportDocumentState;
  onDocumentStateChange?: (next: ReportDocumentState) => void;
  autosave?: (snapshot: {
    patch: ReportPatch;
    structuredDraft?: WorkshopStructuredDraftState | null;
    documentMarkdown?: string;
  }) => void | Promise<void>;
  onRewriteRequested?: (patch: ReportPatch, style: PatchRewriteStyle) => void;
}

export interface PatchLifecycleResult {
  patch: ReportPatch;
  validation: FormatValidationResult;
}

export function useDocumentPatch(options: UseDocumentPatchOptions = {}) {
  const [pendingPatches, setPendingPatches] = useState<ReportPatch[]>([]);
  const [acceptedPatches, setAcceptedPatches] = useState<ReportPatch[]>([]);
  const [rejectedPatches, setRejectedPatches] = useState<ReportPatch[]>([]);
  const [activePatch, setActivePatch] = useState<ReportPatch | null>(null);
  const [validationResult, setValidationResult] = useState<FormatValidationResult | null>(null);

  const documentState = options.documentState ?? createInitialReportDocumentState();

  const normalizePatch = useCallback(
    (rawPatch: RawWorkshopPatch): ReportPatch => {
      return isReportPatch(rawPatch)
        ? rawPatch
        : convertWorkshopDraftPatchToReportPatch(rawPatch, { structuredDraft: options.structuredDraft });
    },
    [options.structuredDraft],
  );

  const validatePatch = useCallback(
    (patch: ReportPatch): FormatValidationResult => validateReportPatch(patch, documentState),
    [documentState],
  );

  const receivePatch = useCallback(
    (rawPatch: RawWorkshopPatch): PatchLifecycleResult => {
      const patch = {
        ...normalizePatch(rawPatch),
        status: 'pending' as const,
        requiresApproval: true,
      };
      const validation = validatePatch(patch);
      setPendingPatches((prev) => mergePatchById(prev, patch));
      setActivePatch(patch);
      setValidationResult(validation);
      return { patch, validation };
    },
    [normalizePatch, validatePatch],
  );

  const applyPatch = useCallback(
    async (patchOrId: ReportPatch | string): Promise<PatchLifecycleResult> => {
      const pending = typeof patchOrId === 'string'
        ? pendingPatches.find((candidate) => candidate.patchId === patchOrId)
        : patchOrId;
      if (!pending) {
        throw new Error('Patch was not found.');
      }

      const acceptedPatch = { ...pending, status: 'accepted' as const };
      const validation = validatePatch(acceptedPatch);
      setValidationResult(validation);
      if (!validation.valid) {
        toast.error(validation.errors[0] || '문서 반영 제안을 먼저 수정해야 합니다.');
        return { patch: acceptedPatch, validation };
      }

      const adapter = options.getEditorAdapter?.() ?? null;
      if (!adapter) {
        toast.error('문서 편집기가 아직 준비되지 않았습니다.');
        return { patch: acceptedPatch, validation };
      }

      await adapter.applyReportPatch(acceptedPatch);

      let nextStructuredDraft = options.structuredDraft ?? null;
      if (nextStructuredDraft && acceptedPatch.type === 'content') {
        const applied = applyReportPatchToStructuredDraft(nextStructuredDraft, acceptedPatch, { approved: true });
        if (!applied.applied) {
          toast.error('학생 작성 내용 보호 정책 때문에 patch를 반영하지 못했습니다.');
          return { patch: acceptedPatch, validation };
        }
        nextStructuredDraft = applied.next;
        options.onStructuredDraftChange?.(applied.next);
        options.onDocumentStateChange?.(structuredDraftToReportDocumentState(applied.next));
      }

      const appliedPatch = { ...acceptedPatch, status: 'applied' as const };
      setPendingPatches((prev) => prev.filter((candidate) => candidate.patchId !== pending.patchId));
      setAcceptedPatches((prev) => mergePatchById(prev, appliedPatch));
      setActivePatch(null);
      await options.autosave?.({
        patch: appliedPatch,
        structuredDraft: nextStructuredDraft,
        documentMarkdown: String(adapter.getDocumentMarkdown?.() || ''),
      });
      return { patch: appliedPatch, validation };
    },
    [options, pendingPatches, validatePatch],
  );

  const rejectPatch = useCallback(
    (patchOrId: ReportPatch | string) => {
      const patch = typeof patchOrId === 'string'
        ? pendingPatches.find((candidate) => candidate.patchId === patchOrId)
        : patchOrId;
      if (!patch) return;
      const rejectedPatch = { ...patch, status: 'rejected' as const };
      setPendingPatches((prev) => prev.filter((candidate) => candidate.patchId !== patch.patchId));
      setRejectedPatches((prev) => mergePatchById(prev, rejectedPatch));
      setActivePatch((current) => (current?.patchId === patch.patchId ? null : current));
    },
    [pendingPatches],
  );

  const requestPatchRewrite = useCallback(
    (patch: ReportPatch, style: PatchRewriteStyle) => {
      const supersededPatch = { ...patch, status: 'superseded' as const };
      setPendingPatches((prev) => mergePatchById(prev, supersededPatch));
      options.onRewriteRequested?.(supersededPatch, style);
      return { patch: supersededPatch, style };
    },
    [options],
  );

  const editPatchBeforeApply = useCallback((patch: ReportPatch) => {
    setActivePatch(patch);
    return patch;
  }, []);

  return useMemo(
    () => ({
      pendingPatches,
      acceptedPatches,
      rejectedPatches,
      activePatch,
      validationResult,
      receivePatch,
      normalizePatch,
      validatePatch,
      applyPatch,
      rejectPatch,
      requestPatchRewrite,
      editPatchBeforeApply,
      queuePatch: receivePatch,
      approvePatch: applyPatch,
    }),
    [
      acceptedPatches,
      activePatch,
      applyPatch,
      editPatchBeforeApply,
      normalizePatch,
      pendingPatches,
      receivePatch,
      rejectPatch,
      rejectedPatches,
      requestPatchRewrite,
      validatePatch,
      validationResult,
    ],
  );
}

function mergePatchById<T extends ReportPatch>(patches: T[], patch: T): T[] {
  const exists = patches.some((candidate) => candidate.patchId === patch.patchId);
  if (!exists) {
    return [...patches, patch];
  }
  return patches.map((candidate) => (candidate.patchId === patch.patchId ? patch : candidate));
}
