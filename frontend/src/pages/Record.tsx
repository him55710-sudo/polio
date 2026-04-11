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
import { 
  DocumentStatus, 
  IN_PROGRESS_STATUSES, 
  SUCCESS_STATUSES,
  TERMINAL_STATUSES
} from '../types/domain';
import { useAsyncJob } from '../hooks/useAsyncJob';

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
  };
}

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

  useAsyncJob<DocumentStatusResponse>({
    url: document && IN_PROGRESS_STATUSES.has(document.status) ? `/api/v1/documents/${document.id}` : null,
    isTerminal: (data) => TERMINAL_STATUSES.has(data.status),
    onSuccess: (fresh) => {
      setDocument(fresh);
    },
    onError: (error) => {
      console.error('Failed to poll document status:', error);
    },
  });

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
    <div className="mx-auto max-w-7xl animate-in fade-in slide-in-from-bottom-4 duration-1000">
      <div className="relative mb-10 overflow-hidden rounded-[2.5rem] bg-[#004aad] p-8 md:p-12">
        {/* Background Decorative Elements */}
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-white/10 blur-3xl" />
        <div className="absolute -bottom-20 -left-20 h-64 w-64 rounded-full bg-[#00c2ff]/20 blur-3xl" />
        
        <div className="relative z-10">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-1.5 backdrop-blur-md">
            <ShieldCheck size={14} className="text-[#00c2ff]" />
            <span className="text-sm font-bold tracking-tight text-[#00c2ff]">기능: 기록 업로드</span>
          </div>
          
          <h1 className="text-3xl font-black tracking-tight text-white md:text-5xl lg:leading-[1.15]">
            학생부 PDF를 <br className="hidden sm:block" />
            <span className="text-[#00c2ff]">안전하게</span> 분석할게요
          </h1>
          
          <div className="mt-6 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <p className="max-w-xl text-lg font-medium leading-relaxed text-blue-100/80">
              업로드한 문서는 개인정보 숨김 처리 후 AI가 꼼꼼히 읽어봅니다.<br />
              분석이 끝나면 곧바로 대학 합격 진단과 세특 작성을 시작할 수 있어요.
            </p>
            
            <div className="flex shrink-0 flex-col items-start gap-3 lg:items-end">
              <div className="flex gap-2">
                <StatusBadge status={document?.status === 'failed' ? 'danger' : document && SUCCESS_STATUSES.has(document.status) ? 'success' : 'active'}>
                  {document ? formatStatusLabel(document.status) : '업로드 대기 중'}
                </StatusBadge>
                {document && (
                  <div className="flex items-center gap-1.5 rounded-full bg-white/5 px-3 py-1 font-bold text-white/90 backdrop-blur-sm">
                    <TimerReset size={12} />
                    <span className="text-xs">분석 시도 {document.parse_attempts}회</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SectionCard
          title="빠른 업로드 가이드"
          description="정확한 분석을 위해 아래 항목을 확인해 주세요."
          eyebrow="체크리스트"
          className="h-full border-none bg-white/40 shadow-xl shadow-blue-900/5 backdrop-blur-xl"
        >
          <div className="space-y-4">
            <div className="rounded-2xl bg-emerald-50/50 p-6 ring-1 ring-inset ring-emerald-500/20">
              <p className="flex items-center gap-2 text-base font-black text-emerald-900">
                <CheckCircle2 size={18} className="text-emerald-600" />
                업로드 전 필수 체크리스트
              </p>
              <ul className="mt-4 space-y-3">
                {UPLOAD_READY_CHECKLIST.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-3 text-sm font-semibold leading-relaxed text-emerald-800/80">
                    <div className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            
            <button
              type="button"
              onClick={() => navigate('/app/help/student-record-pdf')}
              className="group flex w-full items-center justify-between rounded-xl bg-white p-4 font-bold text-[#004aad] shadow-sm transition-all hover:bg-[#004aad] hover:text-white"
            >
              <span className="text-sm">학생부 PDF 다운로드/저장 방법 보기</span>
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </button>
          </div>
        </SectionCard>

        {shouldShowTimingDashboard ? (
          <div className="h-full animate-in fade-in zoom-in-95 duration-500">
            <ProcessTimingDashboard
              phases={timingPhaseItems}
              title="분석 리포트 생성 타임라인"
              description="데이터 마스킹과 내용 추출이 현재 진행 중입니다."
            />
          </div>
        ) : (
          <SectionCard
            title="다음 단계 안내"
            description="분석이 완료되면 무엇을 할 수 있나요?"
            eyebrow="다음 단계"
            className="h-full border-none bg-white/40 shadow-xl shadow-blue-900/5 backdrop-blur-xl"
          >
            <div className="space-y-4">
              <div className="flex gap-4 rounded-2xl bg-slate-50 p-4 transition-colors hover:bg-white">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-100 text-blue-600">
                  <FileSearch size={20} />
                </div>
                <div>
                  <p className="font-bold text-slate-900">목표 대학 진단</p>
                  <p className="mt-1 text-sm text-slate-500">지망 학과와 내 학생부의 일치도를 분석합니다.</p>
                </div>
              </div>
              <div className="flex gap-4 rounded-2xl bg-slate-50 p-4 transition-colors hover:bg-white">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-purple-100 text-purple-600">
                  <FileText size={20} />
                </div>
                <div>
                  <p className="font-bold text-slate-900">AI 세특 워크숍</p>
                  <p className="mt-1 text-sm text-slate-500">부족한 활동을 채우고 매력적인 세특을 작성합니다.</p>
                </div>
              </div>
            </div>
          </SectionCard>
        )}
      </div>

      <div className="my-10 h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent" />

      <StepIndicator items={stepItems} />

      <div className="grid grid-cols-1 gap-8 xl:grid-cols-[1fr_0.8fr]">
        <div className="space-y-6">
          <SectionCard 
            title="문서 업로드" 
            description="PDF 1개(최대 50MB) 업로드를 지원합니다." 
            eyebrow="문서"
            className="border-none bg-white/40 shadow-xl shadow-blue-900/5 backdrop-blur-xl"
          >
            <div className="space-y-8">
              <CatalogAutocompleteInput
                label="목표 학과 설정 (선별 분석용)"
                value={targetMajor}
                onChange={setTargetMajor}
                onSelect={suggestion => setTargetMajor(suggestion.label)}
                placeholder="예: 경영학과, 인공지능공학과"
                suggestions={majorSuggestions}
                helperText={goalList.length > 0 ? `현재 설정된 목표: ${goalList[0].university} ${goalList[0].major}` : "학과를 입력하면 해당 분야에 최적화된 분석 결과를 제공해 드려요."}
                emptyText="일치하는 학과가 없지만, 그대로 입력하고 진행하실 수 있어요."
                inputClassName="bg-white/50 border-slate-200 focus:bg-white"
              />

              <div
                {...getRootProps({
                  onClick: handleOpenFileDialog,
                  onKeyDown: handleDropzoneKeyDown,
                })}
                className={`group relative overflow-hidden rounded-[2rem] border-2 border-dashed p-8 transition-all md:p-12 ${
                  isDragActive 
                    ? 'border-[#004aad] bg-[#004aad]/5 scale-[1.01]' 
                    : 'border-slate-200 bg-slate-50/50 hover:border-[#004aad]/30 hover:bg-white hover:shadow-2xl hover:shadow-blue-900/5'
                } ${isBusy ? 'cursor-not-allowed opacity-70' : 'cursor-pointer'}`}
              >
                <input {...getInputProps({ 'aria-label': '학생부 PDF 업로드' })} />
                
                <div className="relative z-10 flex flex-col items-center text-center">
                  <div className={`mb-6 flex h-20 w-20 items-center justify-center rounded-[2.5rem] transition-all duration-500 ${
                    isBusy ? 'bg-slate-100 text-slate-400 animate-pulse' : 'bg-white text-[#004aad] shadow-xl group-hover:scale-110 group-hover:rotate-12'
                  }`}>
                    <FileUp size={32} />
                  </div>
                  
                  <h2 className="text-2xl font-black text-slate-900">PDF 파일을 여기에 놓아주세요</h2>
                  <p className="mt-3 text-lg font-medium text-slate-500">
                    또는 <span className="text-[#004aad] underline decoration-2 underline-offset-4">파일 선택</span> 버튼을 눌러주세요.
                  </p>
                  
                  <div className="mt-8 flex flex-wrap justify-center gap-3">
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-200/50 px-3 py-1 text-xs font-bold text-slate-600 backdrop-blur-sm">
                      최대 50MB
                    </span>
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-200/50 px-3 py-1 text-xs font-bold text-slate-600 backdrop-blur-sm">
                      PDF 전용
                    </span>
                  </div>
                </div>

                {isBusy && (
                  <div className="absolute inset-0 bg-white/20 backdrop-blur-[2px]" />
                )}
              </div>

              {document && (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  {[
                    { label: '파일명', value: document.original_filename || '-', full: true },
                    { label: '파일 용량', value: formatBytes(document.file_size_bytes ?? null) },
                    { label: '전체 페이지', value: `${document.page_count ?? 0}p` },
                    { label: '데이터 항목', value: `${document.parse_metadata?.chunk_count ?? 0}개` },
                  ].map((stat, idx) => (
                    <div key={idx} className={`rounded-2xl bg-slate-50/50 p-4 ring-1 ring-inset ring-slate-200/50 ${stat.full ? 'col-span-2' : ''}`}>
                      <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">{stat.label}</p>
                      <p className="mt-1 truncate text-sm font-bold text-slate-700">{stat.value}</p>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex flex-wrap items-center gap-4 pt-4">
                <PrimaryButton 
                  size="lg"
                  className="px-8 shadow-xl shadow-blue-600/20"
                  onClick={() => navigate(diagnosisPath)} 
                  disabled={!canContinue}
                >
                  기록 진단 시작하기
                  <ArrowRight size={18} />
                </PrimaryButton>
                
                <SecondaryButton
                  size="lg"
                  variant="outline"
                  onClick={() => navigate(`/app/workshop/${document?.project_id}?major=${encodeURIComponent(targetMajor.trim())}`)}
                  disabled={!canContinue}
                >
                  워크숍으로 이동
                </SecondaryButton>

                {document?.status === 'failed' && (
                  <button
                    onClick={() => startParse(document.id, 'retry')}
                    disabled={isBusy}
                    className="ml-auto inline-flex items-center gap-2 font-bold text-rose-600 hover:text-rose-700 disabled:opacity-50"
                  >
                    <TimerReset size={16} />
                    다시 시도
                  </button>
                )}
              </div>
            </div>
          </SectionCard>
        </div>

        <div className="flex flex-col gap-6">
          <SectionCard 
            title="보호 및 보안 설정" 
            description="데이터는 안전하게 보호됩니다." 
            eyebrow="보안" 
            className="border-none bg-white/40 shadow-xl shadow-blue-900/5 backdrop-blur-xl"
            collapsible
          >
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="rounded-2xl bg-slate-50/50 p-4 ring-1 ring-inset ring-slate-200/50">
                <p className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-slate-400">
                  <ShieldCheck size={12} className="text-blue-500" />
                  보안 처리 건수
                </p>
                <p className="mt-2 text-lg font-black text-slate-700">{maskingSummary?.replacement_count ?? 0}<span className="text-xs font-medium text-slate-400 ml-1">건 처리됨</span></p>
              </div>
              <div className="rounded-2xl bg-slate-50/50 p-4 ring-1 ring-inset ring-slate-200/50">
                <p className="text-xs font-black uppercase tracking-widest text-slate-400">문서 인식 지표</p>
                <p className="mt-2 text-lg font-black text-slate-700">{document?.parse_metadata?.table_count ?? 0}<span className="text-xs font-medium text-slate-400 ml-1">개 객체 인식</span></p>
              </div>
            </div>
          </SectionCard>

          {document?.parse_metadata?.warnings?.length ? (
            <SectionCard 
              title="분석 리포트 알림" 
              description="내용 확인 과정에서 참조가 필요한 사항입니다." 
              eyebrow="알림"
              className="border-none bg-amber-50 shadow-xl shadow-amber-900/5 backdrop-blur-xl"
            >
              <div className="space-y-3">
                {document.parse_metadata.warnings.map((warning, idx) => (
                  <div key={idx} className="flex gap-3 rounded-xl bg-white/60 p-4 ring-1 ring-inset ring-amber-200">
                    <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-amber-500" />
                    <p className="text-sm font-semibold leading-relaxed text-amber-900">{warning}</p>
                  </div>
                ))}
              </div>
            </SectionCard>
          ) : (
            <div className="rounded-[2rem] bg-emerald-50 p-8 shadow-xl shadow-emerald-900/5 ring-1 ring-inset ring-emerald-100">
              <div className="flex gap-5">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-500 text-white shadow-lg shadow-emerald-200">
                  <CheckCircle2 size={24} />
                </div>
                <div>
                  <h3 className="text-lg font-black text-emerald-900">분석이 완벽하게 완료되었어요!</h3>
                  <p className="mt-1 text-sm font-semibold leading-relaxed text-emerald-800/70">
                    문서에서 어떠한 결함도 발견되지 않았습니다. <br className="hidden sm:block" />
                    이제 목표 대학 합격 가능성을 정밀하게 진단할 준비가 되었습니다.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
