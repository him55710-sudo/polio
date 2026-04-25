import { useCallback, useMemo, type RefObject } from 'react';
import type { TiptapEditorHandle } from '../../../components/editor/TiptapEditor';
import { TiptapEditorAdapter } from '../adapters/TiptapEditorAdapter';
import type { EditorAdapter } from '../adapters/EditorAdapter';
import type {
  ReportDocumentState,
  ReportPatch,
  UniFoliReportSectionId,
} from '../types/reportDocument';
import type { WorkshopStructuredDraftState } from '../../../lib/workshopCoauthoring';

interface UseEditorBridgeOptions {
  editorRef: RefObject<TiptapEditorHandle | null>;
  documentState?: ReportDocumentState | null;
  setDocumentState?: (state: ReportDocumentState) => void;
  structuredDraft?: WorkshopStructuredDraftState | null;
  setStructuredDraft?: (state: WorkshopStructuredDraftState) => void;
}

export interface EditorSnapshot {
  json: unknown;
  html: string;
  markdown: string;
}

export function useEditorBridge(input: RefObject<TiptapEditorHandle | null> | UseEditorBridgeOptions) {
  const options = isRefObject(input) ? { editorRef: input } : input;

  const getEditorAdapter = useCallback((): EditorAdapter | null => {
    if (!options.editorRef.current) {
      return null;
    }
    return new TiptapEditorAdapter(options.editorRef.current);
  }, [options.editorRef]);

  const editorAdapter = useMemo(() => getEditorAdapter(), [getEditorAdapter]);

  const getEditorSnapshot = useCallback((): EditorSnapshot | null => {
    const adapter = getEditorAdapter();
    if (!adapter) {
      return null;
    }
    const html = String(adapter.getDocumentHTML() || '');
    const markdown = String(adapter.getDocumentMarkdown?.() || html);
    return {
      json: adapter.getDocumentJSON(),
      html,
      markdown,
    };
  }, [getEditorAdapter]);

  const applyReportPatchToEditor = useCallback(
    async (patch: ReportPatch) => {
      const adapter = getEditorAdapter();
      if (!adapter) {
        throw new Error('Editor is not ready.');
      }
      await adapter.applyReportPatch(patch);
      return getEditorSnapshot();
    },
    [getEditorAdapter, getEditorSnapshot],
  );

  const focusSection = useCallback(
    (sectionId: UniFoliReportSectionId) => {
      const adapter = getEditorAdapter();
      adapter?.focusSection(sectionId);
    },
    [getEditorAdapter],
  );

  const syncStructuredDraftFromEditor = useCallback(() => {
    // TODO: Parse editor markdown back into section-id aware structuredDraft once section nodes carry stable ids.
    return {
      structuredDraft: options.structuredDraft ?? null,
      editorSnapshot: getEditorSnapshot(),
      documentState: options.documentState ?? null,
    };
  }, [getEditorSnapshot, options.documentState, options.structuredDraft]);

  return {
    editorAdapter,
    getEditorAdapter,
    getEditorSnapshot,
    applyReportPatchToEditor,
    focusSection,
    syncStructuredDraftFromEditor,
  };
}

function isRefObject(value: RefObject<TiptapEditorHandle | null> | UseEditorBridgeOptions): value is RefObject<TiptapEditorHandle | null> {
  return 'current' in value;
}
