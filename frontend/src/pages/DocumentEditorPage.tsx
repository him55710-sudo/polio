import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ChevronLeft,
  Save,
  FileText,
  Loader2,
  Check,
  Download,
  BookOpen,
} from 'lucide-react';
import toast from 'react-hot-toast';
import type { JSONContent } from '@tiptap/react';
import { api } from '../lib/api';
import { TiptapEditor, type TiptapEditorHandle } from '../components/editor/TiptapEditor';
import { ExportModal } from '../components/editor/ExportModal';
import { PrimaryButton, SecondaryButton } from '../components/primitives';

interface Draft {
  id: string;
  project_id: string;
  title: string;
  content_markdown: string;
  content_json: string | null;
  status: string;
}

export function DocumentEditorPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [draft, setDraft] = useState<Draft | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [isExportOpen, setIsExportOpen] = useState(false);

  const editorRef = useRef<TiptapEditorHandle>(null);
  const pendingContentRef = useRef<JSONContent | null>(null);
  const saveTimerRef = useRef<number | null>(null);

  // ─── Load or create draft ───
  useEffect(() => {
    async function load() {
      if (!projectId) return;
      setIsLoading(true);
      try {
        const drafts = await api.get<Draft[]>(`/api/v1/projects/${projectId}/drafts`);
        if (drafts && drafts.length > 0) {
          setDraft(drafts[0]);
        } else {
          const newDraft = await api.post<Draft>(`/api/v1/projects/${projectId}/drafts`, {
            title: '새 탐구 보고서',
            content_markdown: '',
            content_json: null,
          });
          setDraft(newDraft);
        }
      } catch (err) {
        console.error('Load draft failed:', err);
        setDraft({
          id: 'local',
          project_id: projectId,
          title: '새 탐구 보고서 (오프라인)',
          content_markdown: '',
          content_json: null,
          status: 'in_progress',
        });
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [projectId]);

  // ─── Persist to server ───
  const flushSave = useCallback(async () => {
    const content = pendingContentRef.current;
    if (!content || !projectId || !draft || draft.id === 'local') return;
    if (isSaving) return;

    setIsSaving(true);
    try {
      await api.patch(`/api/v1/projects/${projectId}/drafts/${draft.id}`, {
        content_json: JSON.stringify(content),
      });
      setLastSaved(new Date());
      pendingContentRef.current = null;
    } catch (err) {
      console.error('Auto-save failed:', err);
    } finally {
      setIsSaving(false);
    }
  }, [projectId, draft, isSaving]);

  // ─── Debounced auto-save ───
  const handleEditorUpdate = useCallback(
    (json: JSONContent) => {
      pendingContentRef.current = json;
      if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
      saveTimerRef.current = window.setTimeout(() => flushSave(), 2000);
    },
    [flushSave],
  );

  // ─── Manual save ───
  const handleManualSave = useCallback(async () => {
    if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    const json = editorRef.current?.getJSON();
    if (json) pendingContentRef.current = json;
    await flushSave();
    toast.success('문서를 저장했습니다.');
  }, [flushSave]);

  // ─── Cleanup ───
  useEffect(() => {
    return () => {
      if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    };
  }, []);

  // ─── Resolve initial content ───
  const initialContent = draft?.content_json ? JSON.parse(draft.content_json) : null;

  // ─── Loading ───
  if (isLoading) {
    return (
      <div className="flex h-[80vh] w-full items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-100">
              <FileText size={28} className="text-blue-600" />
            </div>
            <Loader2 size={20} className="absolute -bottom-1 -right-1 animate-spin text-blue-600" />
          </div>
          <p className="text-sm font-medium text-slate-500">문서를 준비하고 있습니다...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-64px)] flex-col overflow-hidden bg-slate-50">
      {/* ─── Top bar ─── */}
      <header className="flex h-14 w-full shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 lg:px-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-50 hover:text-slate-700"
          >
            <ChevronLeft size={18} />
          </button>
          <div className="h-6 w-px bg-slate-200" />
          <div className="flex flex-col gap-0.5">
            <div className="flex items-center gap-2">
              <BookOpen size={16} className="text-blue-600" />
              <h1 className="max-w-[300px] truncate text-sm font-bold text-slate-900">
                {draft?.title || '문서 편집기'}
              </h1>
            </div>
            <p className="text-[10px] font-medium text-slate-400">
              {isSaving ? (
                <span className="inline-flex items-center gap-1">
                  <Loader2 size={9} className="animate-spin" /> 저장 중...
                </span>
              ) : lastSaved ? (
                <span className="inline-flex items-center gap-1">
                  <Check size={9} className="text-emerald-500" />
                  {lastSaved.toLocaleTimeString()} 저장됨
                </span>
              ) : (
                '편집 시 자동 저장'
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <SecondaryButton size="sm" onClick={() => setIsExportOpen(true)}>
            <Download size={14} />
            <span className="hidden sm:inline">내보내기</span>
          </SecondaryButton>
          <PrimaryButton size="sm" onClick={handleManualSave} disabled={isSaving}>
            <Save size={14} />
            <span className="hidden sm:inline">저장</span>
          </PrimaryButton>
        </div>
      </header>

      {/* ─── Editor ─── */}
      <main className="flex-1 overflow-hidden">
        <TiptapEditor ref={editorRef} initialContent={initialContent} onUpdate={handleEditorUpdate} />
      </main>

      {/* ─── Export Modal ─── */}
      <ExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        documentTitle={draft?.title || '탐구보고서'}
        getJSON={() => editorRef.current?.getJSON() || { type: 'doc', content: [] }}
        getHTML={() => editorRef.current?.getHTML() || ''}
      />
    </div>
  );
}
