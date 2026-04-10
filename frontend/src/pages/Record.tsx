import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  ArrowRight,
  CheckCircle2,
  FileSearch,
  FileText,
  FileUp,
  ShieldCheck,
  TimerReset,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import { ProcessTimingDashboard, type TimingPhaseStatus } from '../components/ProcessTimingDashboard';
import { api, shouldUseSynchronousApiJobs } from '../lib/api';
import { getApiErrorMessage } from '../lib/apiError';
import { searchMajors } from '../lib/educationCatalog';
import { buildRankedGoals } from '../lib/rankedGoals';
import { CatalogAutocompleteInput } from '../components/CatalogAutocompleteInput';
import { useAuthStore } from '../store/authStore';
import {
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionCard,
  StatusBadge,
  StepIndicator,
  SurfaceCard,
  WorkflowNotice,
} from '../components/primitives';

type DocumentStatus = 'uploaded' | 'masking' | 'parsing' | 'retrying' | 'parsed' | 'partial' | 'failed';
type MaskingStatus = 'pending' | 'masking' | 'masked' | 'failed';
const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;
type RecordTimingPhaseKey = 'upload' | 'parse';

interface RecordTimingPhaseState {
  status: TimingPhaseStatus;
  startedAt: number | null;
  finishedAt: number | null;
  note?: string;
}

type RecordTimingPhaseMap = Record<RecordTimingPhaseKey, RecordTimingPhaseState>;

interface DocumentStatusResponse {
  id: string;
  project_id: string;
  upload_asset_id: string;
  original_filename: string | null;
  content_type: string | null;
  file_size_bytes: number | null;
  sha256: string | null;
  stored_path: string | null;
  upload_status: string | null;
  parser_name: string;
  source_extension: string;
  status: DocumentStatus;
  masking_status: MaskingStatus;
  parse_attempts: number;
  last_error: string | null;
  can_retry: boolean;
  latest_async_job_id: string | null;
  latest_async_job_status: string | null;
  latest_async_job_error: string | null;
  page_count: number;
  word_count: number;
  parse_started_at: string | null;
  parse_completed_at: string | null;
  created_at: string;
  updated_at: string;
  content_text: string;
  content_markdown: string;
  parse_metadata: {
    source_storage_provider?: string;
    source_storage_key?: string;
    chunk_count?: number;
    table_count?: number;
    warnings?: string[];
    masking?: {
      methods?: string[];
      replacement_count?: number;
      pattern_hits?: Record<string, number>;
    };
    page_failures?: Array<{ page_number?: number; message?: string }>;
    pdf_analysis?: {
      provider?: string;
      model?: string;
      engine?: string;
      generated_at?: string;
      failure_reason?: string;
      attempted_provider?: string;
      attempted_model?: string;
      recovered_from_text_fallback?: boolean;
      requested_pdf_analysis_provider?: string;
      requested_pdf_analysis_model?: string;
      actual_pdf_analysis_provider?: string;
      actual_pdf_analysis_model?: string;
      pdf_analysis_engine?: string;
      fallback_used?: boolean;
      fallback_reason?: string;
      processing_duration_ms?: number;
      summary?: string;
      key_points?: string[];
      evidence_gaps?: string[];
      page_insights?: Array<{ page_number?: number; summary?: string }>;
    };
    student_record_canonical?: {
      schema_version?: string;
      document_confidence?: number;
      timeline_signals?: Array<{ signal?: string }>;
      grades_subjects?: Array<{ subject?: string }>;
      subject_special_notes?: Array<{ label?: string }>;
      extracurricular?: Array<{ label?: string }>;
      career_signals?: Array<{ label?: string }>;
      reading_activity?: Array<{ label?: string }>;
      behavior_opinion?: Array<{ label?: string }>;
      major_alignment_hints?: Array<{ hint?: string }>;
      weak_or_missing_sections?: Array<{ section?: string; status?: string }>;
      uncertainties?: Array<{ message?: string }>;
    };
  };
}

const IN_PROGRESS_STATUSES = new Set<DocumentStatus>(['masking', 'parsing', 'retrying']);
const SUCCESS_STATUSES = new Set<DocumentStatus>(['parsed', 'partial']);

const UPLOAD_READY_CHECKLIST = [
  '파일 확장자가 .pdf인지 확인하기',
  '용량이 50MB 이하인지 확인하기',
  '학생부 전체 페이지가 모두 포함됐는지 확인하기',
] as const;

function createInitialTimingPhases(): RecordTimingPhaseMap {
  return {
    upload: { status: 'idle', startedAt: null, finishedAt: null, note: '파일 업로드 준비 중' },
    parse: { status: 'idle', startedAt: null, finishedAt: null, note: '문서 내용을 확인할 준비 중' },
  };
}

function formatBytes(value: number | null): string {

function formatBytes(value: number | null): string {
  if (!value) return '0 B';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function ProvenanceName(type: string) {
  switch (type) {
    case 'student_record': return '학생부 기록';
    case 'external_research': return '외부 문헌 및 기준';
    case 'ai_interpretation': return 'AI 심층 분석';
    default: return type;
  }
}

function formatStatusLabel(status: DocumentStatus): string {
  switch (status) {
    case 'uploaded':
      return '업로드 완료';
    case 'masking':
      return '보안 처리 중';
    case 'parsing':
      return '분석 중';
    case 'retrying':
      return '재시도 중';
    case 'parsed':
      return '분석 완료';
    case 'partial':
      return '분석 완료(일부 경고)';
    case 'failed':
      return '오류 발생';
    default:
      return status;
  }
}

function getStepState(
  document: DocumentStatusResponse | null,
  step: 'upload' | 'masking' | 'parsing',
): 'done' | 'active' | 'pending' | 'error' {
  if (!document) return 'pending';
  if (step === 'upload') return 'done';
  if (step === 'masking') {
    if (document.masking_status === 'failed') return 'error';
    if (document.masking_status === 'masked') return 'done';
    if (document.masking_status === 'masking' || IN_PROGRESS_STATUSES.has(document.status)) return 'active';
    return 'pending';
  }
  if (document.status === 'failed') return 'error';
  if (document.status === 'parsed' || document.status === 'partial') return 'done';
  if (IN_PROGRESS_STATUSES.has(document.status)) return 'active';
  return 'pending';
}

export function Record() {
  const navigate = useNavigate();
  const { user: authUser, isGuestSession } = useAuth();
  const { user: profileUser } = useAuthStore();

  const [targetMajor, setTargetMajor] = useState('');
  
  const goalList = useMemo(() => buildRankedGoals(profileUser, 6), [profileUser]);

  useEffect(() => {
    const preferredMajor = profileUser?.target_major?.trim() || goalList[0]?.major || '';
    if (preferredMajor && !targetMajor) {
      setTargetMajor(preferredMajor);
    }
  }, [goalList, profileUser?.target_major, targetMajor]);
  const [document, setDocument] = useState<DocumentStatusResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isStartingParse, setIsStartingParse] = useState(false);
  const [timingPhases, setTimingPhases] = useState<RecordTimingPhaseMap>(() => createInitialTimingPhases());
  const lastTerminalStatus = useRef<DocumentStatus | null>(null);
  const useSynchronousApiJobs = shouldUseSynchronousApiJobs();

  const setTimingPhase = useCallback(
    (phase: RecordTimingPhaseKey, updater: Partial<RecordTimingPhaseState> | ((prev: RecordTimingPhaseState) => RecordTimingPhaseState)) => {
      setTimingPhases((prev) => {
        const current = prev[phase];
        const next = typeof updater === 'function' ? updater(current) : { ...current, ...updater };
        return { ...prev, [phase]: next };
      });
    },
    [],
  );

  const beginTimingPhase = useCallback((phase: RecordTimingPhaseKey, note?: string) => {
    const now = Date.now();
    setTimingPhase(phase, {
      status: 'running',
      startedAt: now,
      finishedAt: null,
      note,
    });
  }, [setTimingPhase]);

  const finishTimingPhase = useCallback((phase: RecordTimingPhaseKey, status: Exclude<TimingPhaseStatus, 'idle'>, note?: string) => {
    const now = Date.now();
    setTimingPhase(phase, (prev) => ({
      ...prev,
      status,
      startedAt: prev.startedAt ?? now,
      finishedAt: now,
      note: note ?? prev.note,
    }));
  }, [setTimingPhase]);

  const failRunningTimingPhases = useCallback((note?: string) => {
    const now = Date.now();
    setTimingPhases((prev) => {
      const next = { ...prev };
      (Object.keys(next) as RecordTimingPhaseKey[]).forEach((phase) => {
        if (next[phase].status !== 'running') return;
        next[phase] = {
          ...next[phase],
          status: 'failed',
          finishedAt: now,
          note: note ?? next[phase].note,
        };
      });
      return next;
    });
  }, []);

  const resetTimingPhases = useCallback(() => {
    setTimingPhases(createInitialTimingPhases());
  }, []);

  const isBusy = isUploading || isStartingParse;

  const majorSuggestions = useMemo(
    () => (targetMajor.trim().length >= 1 ? searchMajors(targetMajor, null, 10) : []),
    [targetMajor],
  );

  useEffect(() => {
    if (!document || !IN_PROGRESS_STATUSES.has(document.status)) return undefined;

    const intervalId = window.setInterval(async () => {
      try {
        const fresh = await api.get<DocumentStatusResponse>(`/api/v1/documents/${document.id}`);
        setDocument(fresh);
      } catch (error) {
        console.error('Failed to poll document status:', error);
      }
    }, 1500);

    return () => window.clearInterval(intervalId);
  }, [document]);

  useEffect(() => {
    if (!document) return;
    if (IN_PROGRESS_STATUSES.has(document.status)) {
      lastTerminalStatus.current = null;
      return;
    }
    if (lastTerminalStatus.current === document.status) return;

    if (document.status === 'parsed') {
      const parseNote = document.page_count ? `분석 완료 (${document.page_count}페이지)` : '분석 완료';
      finishTimingPhase('parse', 'done', parseNote);
      toast.success('업로드와 분석이 모두 완료됐어요.');
    } else if (document.status === 'partial') {
      const partialNote = document.page_count ? `분석 일부 완료 (${document.page_count}페이지)` : '분석 일부 완료';
      finishTimingPhase('parse', 'done', partialNote);
      toast('일부 경고가 있지만 분석은 완료됐어요. 내용을 확인해 주세요.', { icon: '!' });
    } else if (document.status === 'failed') {
      const failureMessage =
        document.latest_async_job_error || document.last_error || '문서 분석에 실패했어요. 파일 상태를 확인한 뒤 다시 시도해 주세요.';
      finishTimingPhase('parse', 'failed', failureMessage);
      toast.error(
        failureMessage,
      );
    }

    lastTerminalStatus.current = document.status;
  }, [document, finishTimingPhase]);

  const startParse = useCallback(async (documentId: string, source: 'initial' | 'retry' = 'retry') => {
    beginTimingPhase('parse', source === 'initial' ? '문서 내용을 꼼꼼하게 읽어보는 중' : '문서를 다시 확인하는 중');
    setIsStartingParse(true);
    try {
      const parseUrl = useSynchronousApiJobs
        ? `/api/v1/documents/${documentId}/parse?wait_for_completion=true`
        : `/api/v1/documents/${documentId}/parse`;
      const started = await api.post<DocumentStatusResponse>(parseUrl);
      setDocument(started);

      if (started.status === 'failed') {
        const failureMessage = started.latest_async_job_error || started.last_error || '분석 시작에 실패했어요.';
        finishTimingPhase('parse', 'failed', failureMessage);
      } else if (SUCCESS_STATUSES.has(started.status)) {
        const parseNote = started.page_count ? `분석 완료 (${started.page_count}페이지)` : '분석 완료';
        finishTimingPhase('parse', 'done', parseNote);
      }
    } catch (error: any) {
      console.error('Failed to start parsing:', error);
      const detail = error.response?.data?.detail || '분석 시작에 실패했어요.';
      finishTimingPhase('parse', 'failed', detail);
      toast.error(detail);
    } finally {
      setIsStartingParse(false);
    }
  }, [beginTimingPhase, finishTimingPhase, useSynchronousApiJobs]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file || isBusy) return;
      if (file.size > MAX_UPLOAD_BYTES) {
        toast.error('파일 용량이 50MB를 초과해 업로드할 수 없습니다.');
        return;
      }

      if (isGuestSession && !authUser) {
        toast.error('현재 게스트 체험 상태에서는 업로드가 제한돼요. 로그인 후 다시 시도해 주세요.');
        navigate('/auth');
        return;
      }

      setIsUploading(true);
      resetTimingPhases();
      beginTimingPhase('upload', '파일 업로드 진행 중');
      const loadingId = toast.loading('PDF를 업로드하고 문서를 준비하는 중이에요...');

      try {
        const formData = new FormData();
        formData.append('file', file);
        if (targetMajor) {
          formData.append('target_major', targetMajor);
          const matchedGoal =
            goalList.find((g) => g.major === targetMajor)
            || goalList[0]
            || (profileUser?.target_university
              ? { university: profileUser.target_university, major: profileUser.target_major || '' }
              : null);
          if (matchedGoal) {
            formData.append('target_university', matchedGoal.university);
            formData.append('title', `${matchedGoal.university} ${targetMajor} 기록 분석`);
          } else {
            formData.append('title', `${targetMajor} 기록 분석`);
          }
        }

        const created = await api.post<DocumentStatusResponse>('/api/v1/documents/upload', formData);
        setDocument(created);
        finishTimingPhase('upload', 'done', `업로드 완료 (${formatBytes(created.file_size_bytes)})`);
        toast.success('업로드 완료! 분석을 시작할게요.', { id: loadingId });
        await startParse(created.id, 'initial');
      } catch (error: any) {
        console.error('Upload flow failed:', error);
        const failureMessage = getApiErrorMessage(error, '업로드에 실패했습니다. 잠시 후 다시 시도해 주세요.');
        failRunningTimingPhases(failureMessage);
        toast.error(failureMessage, { id: loadingId });
      } finally {
        setIsUploading(false);
      }
    },
    [
      beginTimingPhase,
      failRunningTimingPhases,
      finishTimingPhase,
      isBusy,
      isGuestSession,
      navigate,
      resetTimingPhases,
      startParse,
      targetMajor,
      goalList,
      profileUser?.target_major,
      profileUser?.target_university,
      authUser,
    ],
  );

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    disabled: isBusy,
    noClick: true,
    noKeyboard: true,
    useFsAccessApi: false,
  });

  const handleOpenFileDialog = useCallback(() => {
    if (isBusy) return;
    open();
  }, [isBusy, open]);

  const handleDropzoneKeyDown = useCallback((event: React.KeyboardEvent<HTMLDivElement>) => {
    if (isBusy) return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      open();
    }
  }, [isBusy, open]);

  const canContinue = Boolean(document && SUCCESS_STATUSES.has(document.status));
  const maskingSummary = document?.parse_metadata?.masking;
  const stepItems = [
    { id: 'upload', label: '업로드', description: '파일 등록', state: getStepState(document, 'upload') },
    { id: 'masking', label: '보안 처리', description: '개인정보 안전 보호', state: getStepState(document, 'masking') },
    { id: 'parsing', label: '문서 읽기', description: '문서 내용을 꼼꼼히 확인', state: getStepState(document, 'parsing') },
    {
      id: 'done',
      label: '다음 단계 이동',
      description: '진단 또는 워크숍으로 이동',
      state: canContinue ? 'done' : document?.status === 'failed' ? 'error' : 'pending' as 'done' | 'active' | 'pending' | 'error',
    },
  ] as Array<{ id: string; label: string; description: string; state: 'done' | 'active' | 'pending' | 'error' }>;
  const timingPhaseItems = [
    { id: 'upload', label: '업로드', expectedSeconds: 20, ...timingPhases.upload },
    { id: 'parse', label: '문서 읽기', expectedSeconds: 90, ...timingPhases.parse },
  ];
  const shouldShowTimingDashboard = timingPhaseItems.some((phase) => phase.startedAt !== null);
  const diagnosisPath = document?.project_id
    ? `/app/diagnosis?project_id=${encodeURIComponent(document.project_id)}`
    : '/app/diagnosis';

  return (
    <div className="mx-auto max-w-7xl space-y-6 py-4">
      <PageHeader
        eyebrow="기록 업로드"
        title="학생부 PDF를 안전하게 처리해요"
        description="문서를 올리면 개인정보 보호 처리와 내용 분석이 자동으로 진행돼요. 완료되면 바로 작성 화면으로 이동할 수 있어요."
        evidence={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={document?.status === 'failed' ? 'danger' : document && SUCCESS_STATUSES.has(document.status) ? 'success' : 'active'}>
              {document ? formatStatusLabel(document.status) : '업로드 대기'}
            </StatusBadge>
            {document ? <StatusBadge status="neutral">시도 {document.parse_attempts}회</StatusBadge> : null}
          </div>
        }
      />

      <SectionCard
        title="빠른 업로드 가이드"
        description="업로드 전 체크리스트만 확인하고 바로 시작하세요."
        eyebrow="Quick Start"
        className="border-[#004aad]/10 bg-gradient-to-br from-[#004aad]/5 via-white to-[#004aad]/10"
        actions={
          <button
            type="button"
            onClick={() => navigate('/app/help/student-record-pdf')}
            className="inline-flex items-center gap-2 rounded-lg border border-[#004aad]/20 bg-white px-3 py-2 text-xs font-bold text-[#004aad] transition-colors hover:bg-[#004aad]/5"
          >
            학생부 PDF 다운로드 방법 보기
            <ArrowRight size={14} />
          </button>
        }
      >
        <SurfaceCard tone="muted" className="border border-emerald-100 bg-emerald-50/70" padding="sm">
          <p className="text-sm font-black text-emerald-800">업로드 전 체크리스트</p>
          <ul className="mt-2 space-y-2">
            {UPLOAD_READY_CHECKLIST.map(item => (
              <li key={item} className="flex items-start gap-2 text-sm font-semibold leading-6 text-emerald-900 break-keep">
                <CheckCircle2 size={15} className="mt-1 shrink-0 text-emerald-600" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs font-semibold text-emerald-800/90">PDF 발급/저장 방법은 우측 상단 안내 페이지에서 바로 확인할 수 있어요.</p>
        </SurfaceCard>
      </SectionCard>

      <StepIndicator items={stepItems} />
      {shouldShowTimingDashboard ? (
        <ProcessTimingDashboard
          phases={timingPhaseItems}
          title="업로드 진행 타임테이블"
          description="예상 소요시간 대비 현재 진행률을 확인할 수 있어요."
        />
      ) : null}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <SectionCard title="문서 업로드" description="PDF 1개(최대 50MB) 업로드를 지원해요." eyebrow="입력">
          <CatalogAutocompleteInput
            label="목표 학과 (선택)"
            value={targetMajor}
            onChange={setTargetMajor}
            onSelect={suggestion => setTargetMajor(suggestion.label)}
            placeholder="예: 경영학과, 컴퓨터공학과"
            suggestions={majorSuggestions}
            helperText={goalList.length > 0 ? `${goalList[0].university} ${goalList[0].major}가 기본 목표로 설정되었습니다.` : "학과를 입력하면 아래에 관련 학과 목록이 자동으로 뜹니다."}
            emptyText="일치하는 학과가 아직 없어요. 다른 키워드로 검색해 보세요."
            suggestionTestIdPrefix="record-major-suggestion"
            inputTestId="record-target-major"
          />

          <div
            {...getRootProps({
              onClick: handleOpenFileDialog,
              onKeyDown: handleDropzoneKeyDown,
            })}
            className={`cursor-pointer rounded-2xl border-2 border-dashed p-5 text-left transition-all sm:p-8 ${
              isDragActive ? 'border-[#004aad]/40 bg-[#004aad]/5' : 'border-slate-300 bg-slate-50 hover:border-[#004aad]/30 hover:bg-white'
            } ${isBusy ? 'cursor-not-allowed opacity-70' : ''}`}
          >
            <input {...getInputProps({ 'aria-label': '학생부 PDF 업로드' })} />
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#004aad]/10 text-[#004aad]">
                  <FileUp size={26} />
                </div>
                <div className="min-w-0">
                  <h2 className="text-xl font-black text-slate-900 break-keep">PDF 올리기</h2>
                  <p className="mt-1 text-base font-medium leading-7 text-slate-600 break-keep">
                    여기에 파일을 끌어놓거나 버튼으로 선택해 주세요.
                  </p>
                  <p className="mt-2 text-sm font-semibold leading-6 text-slate-500 break-keep">업로드 후 분석은 자동으로 이어집니다.</p>
                  <div className="mt-3">
                    <button
                      type="button"
                      onClick={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        handleOpenFileDialog();
                      }}
                      disabled={isBusy}
                      className="inline-flex items-center gap-2 rounded-xl border border-[#004aad]/20 bg-white px-3 py-2 text-sm font-bold text-[#004aad] shadow-sm transition-colors hover:bg-[#004aad]/5 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <FileText size={15} />
                      파일 선택
                    </button>
                  </div>
                </div>
              </div>
              <StatusBadge status={isBusy ? 'active' : 'neutral'}>{isBusy ? '처리 중' : 'PDF 파일'}</StatusBadge>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <SurfaceCard tone="muted" padding="sm">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">파일명</p>
              <p className="mt-2 text-sm font-bold text-slate-700 break-all">{document?.original_filename || '-'}</p>
            </SurfaceCard>
            <SurfaceCard tone="muted" padding="sm">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">용량</p>
              <p className="mt-2 text-sm font-bold text-slate-700">{formatBytes(document?.file_size_bytes ?? null)}</p>
            </SurfaceCard>
            <SurfaceCard tone="muted" padding="sm">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">페이지</p>
              <p className="mt-2 text-sm font-bold text-slate-700">{document?.page_count ?? 0}p</p>
            </SurfaceCard>
            <SurfaceCard tone="muted" padding="sm">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">읽은 문단 수</p>
              <p className="mt-2 text-sm font-bold text-slate-700">{document?.parse_metadata?.chunk_count ?? 0}개</p>
            </SurfaceCard>
          </div>

          <div className="flex flex-wrap gap-2">
            <SecondaryButton onClick={() => document && startParse(document.id, 'retry')} disabled={!document?.can_retry || isBusy}>
              <TimerReset size={16} />
              분석 다시 시도
            </SecondaryButton>
            <PrimaryButton data-testid="record-go-diagnosis" onClick={() => navigate(diagnosisPath)} disabled={!canContinue}>
              바로 진단하기
              <FileSearch size={16} />
            </PrimaryButton>
            <SecondaryButton
              onClick={() => navigate(`/app/workshop/${document?.project_id}?major=${encodeURIComponent(targetMajor.trim())}`)}
              disabled={!canContinue}
            >
              작성 화면으로 이동
              <ArrowRight size={16} />
            </SecondaryButton>
          </div>
        </SectionCard>

        <div className="space-y-6">
          <SectionCard title="개인정보 보호 요약" description="개인정보 숨김 처리 결과를 확인해요." eyebrow="보안" collapsible defaultCollapsed>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <SurfaceCard tone="muted" padding="sm">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">처리 방식</p>
                <p className="mt-2 text-sm font-bold text-slate-700 break-keep">{maskingSummary?.methods?.join(', ') || '대기 중'}</p>
              </SurfaceCard>
              <SurfaceCard tone="muted" padding="sm">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">보안 처리 건수</p>
                <p className="mt-2 text-sm font-bold text-slate-700">{maskingSummary?.replacement_count ?? 0}건</p>
              </SurfaceCard>
              <SurfaceCard tone="muted" padding="sm">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">문서 구조 인식</p>
                <p className="mt-2 text-sm font-bold text-slate-700">{document?.parse_metadata?.table_count ?? 0}개</p>
              </SurfaceCard>
            </div>
          </SectionCard>
          {document?.parse_metadata?.warnings?.length ? (
            <SectionCard title="분석 관련 알림" description="분석 과정에서 발견된 특이사항입니다." eyebrow="알림" collapsible>
              <div className="space-y-2">
                {document.parse_metadata.warnings.map((warning, idx) => (
                  <SurfaceCard key={idx} tone="muted" padding="sm" className="bg-amber-50 border-amber-100">
                    <p className="text-sm font-medium text-amber-900">{warning}</p>
                  </SurfaceCard>
                ))}
              </div>
            </SectionCard>
          ) : (
            <WorkflowNotice
              tone="success"
              title="분석이 원활하게 완료되었습니다"
              description="문서에 결함이 없으며, 진단 과정을 바로 시작할 수 있습니다."
            />
          )}
        </div>
      </div>
    </div>
  );
}
