import { create } from 'zustand';
import type { WorkshopStructuredDraftState } from '../../../lib/workshopCoauthoring';
import {
  createInitialReportDocumentState,
  type ReportDocumentState,
  type ReportPatch,
  type ResearchCandidate,
} from '../types/reportDocument';

interface WorkshopCopilotState {
  projectId: string | null;
  workshopId: string | null;
  guidedPhase: string | null;
  selectedTopic: string | null;
  selectedOutline: string | null;
  selectedResearchCandidateIds: string[];
  structuredDraft: WorkshopStructuredDraftState | null;
  reportDocumentState: ReportDocumentState;
  pendingPatches: ReportPatch[];
  editorSnapshot: Record<string, unknown> | null;
  researchCandidates: ResearchCandidate[];
  setContext: (context: Partial<Omit<WorkshopCopilotState, 'setContext' | 'queuePatch' | 'removePatch'>>) => void;
  queuePatch: (patch: ReportPatch) => void;
  removePatch: (patchId: string) => void;
}

export const useWorkshopStore = create<WorkshopCopilotState>((set) => ({
  projectId: null,
  workshopId: null,
  guidedPhase: null,
  selectedTopic: null,
  selectedOutline: null,
  selectedResearchCandidateIds: [],
  structuredDraft: null,
  reportDocumentState: createInitialReportDocumentState(),
  pendingPatches: [],
  editorSnapshot: null,
  researchCandidates: [],
  setContext: (context) => set(context),
  queuePatch: (patch) =>
    set((state) => ({
      pendingPatches: [
        ...state.pendingPatches.filter((candidate) => candidate.patchId !== patch.patchId),
        { ...patch, status: 'pending' },
      ],
    })),
  removePatch: (patchId) =>
    set((state) => ({
      pendingPatches: state.pendingPatches.filter((patch) => patch.patchId !== patchId),
    })),
}));
