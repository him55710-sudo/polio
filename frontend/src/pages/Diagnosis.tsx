import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { AlertTriangle, ArrowRight, CheckCircle2, FileUp, Plus, Settings2, Trash2, Zap } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AsyncJobStatusCard } from '../components/AsyncJobStatusCard';
import { UniversityLogo } from '../components/UniversityLogo';
import { ProcessTimingDashboard, type TimingPhaseStatus } from '../components/ProcessTimingDashboard';
import { useAuthStore } from '../store/authStore';
import { useOnboardingStore } from '../store/onboardingStore';
import { api, shouldUseSynchronousApiJobs } from '../lib/api';
import { getApiErrorMessage } from '../lib/apiError';
import { DiagnosisEvidencePanel } from '../components/DiagnosisEvidencePanel';
import { DiagnosisGuidedChoicePanel } from '../components/DiagnosisGuidedChoicePanel';
import { DiagnosisReportPanel } from '../components/DiagnosisReportPanel';
import { ClaimGroundingPanel } from '../components/ClaimGroundingPanel';
import {
  type AsyncJobRead,
  type DiagnosisRunResponse,
  type DiagnosisResultPayload,
  DIAGNOSIS_STORAGE_KEY,
  formatRiskLevel,
  getDiagnosisFailureMessage,
  isDiagnosisComplete,
  isDiagnosisFailed,
  mergeDiagnosisPayload,
  resolveDiagnosisDeliveryState,
} from '../lib/diagnosis';
import { searchUniversities, searchMajors } from '../lib/educationCatalog';
import { buildRankedGoals } from '../lib/rankedGoals';
import { CatalogAutocompleteInput } from '../components/CatalogAutocompleteInput';
import {
  EmptyState,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionCard,
  StatusBadge,
  StepIndicator,
  SurfaceCard,
  WorkflowNotice,
} from '../components/primitives';

type DiagnosisStep = 'GOALS' | 'UPLOAD' | 'ANALYSING' | 'RESULT' | 'FAILED';
const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;
const PARSE_POLL_INTERVAL_MS = 1500;
const PARSE_TIMEOUT_MS = 3 * 60 * 1000;

type DocumentLifecycleStatus = 'uploaded' | 'masking' | 'parsing' | 'retrying' | 'parsed' | 'partial' | 'failed';

function formatStatusLabel(status: DocumentLifecycleStatus): string {
  switch (status) {
    case 'uploaded':
      return '업로드 완료';
    case 'masking':
      return '보안 처리(마스킹) 중';
    case 'parsing':
      return '생활기록부 내용 분석 중';
    case 'retrying':
      return '재분석 시도 중';
    case 'parsed':
      return '분석 완료';
    case 'partial':
      return '분석 완료 (일부 경고)';
    case 'failed':
      return '분석 실패';
    default:
      return '대기 중';
  }
}

type TimingPhaseKey = 'upload' | 'parse' | 'diagnosis';

interface DiagnosisDocumentStatus {
  id: string;
  status: DocumentLifecycleStatus;
  content_text: string;
  page_count?: number;
  latest_async_job_id?: string | null;
  latest_async_job_status?: string | null;
  parse_metadata?: {
    chunk_count?: number;
    source_storage_provider?: string;
    source_storage_key?: string;
    pdf_analysis?: {
      summary?: string;
      requested_pdf_analysis_provider?: string;
      requested_pdf_analysis_model?: string;
      actual_pdf_analysis_provider?: string;
      actual_pdf_analysis_model?: string;
      pdf_analysis_engine?: string;
      fallback_used?: boolean;
      fallback_reason?: string;
      processing_duration_ms?: number;
    };
  };
  latest_async_job_error?: string | null;
  last_error?: string | null;
}

interface TimingPhaseState {
  status: TimingPhaseStatus;
  startedAt: number | null;
  finishedAt: number | null;
  note?: string;
}

type TimingPhaseMap = Record<TimingPhaseKey, TimingPhaseState>;

const PARSE_SUCCESS_STATUSES = new Set<DocumentLifecycleStatus>(['parsed', 'partial']);
const PARSE_TERMINAL_STATUSES = new Set<DocumentLifecycleStatus>(['parsed', 'partial', 'failed']);

function createInitialTimingPhases(): TimingPhaseMap {
  return {
    upload: { status: 'idle', startedAt: null, finishedAt: null, note: '데이터 전송 중' },
    parse: { status: 'idle', startedAt: null, finishedAt: null, note: '생활기록부 정보 추출 중' },
    diagnosis: { status: 'idle', startedAt: null, finishedAt: null, note: 'AI 기반 맞춤형 진단 중' },
  };
}

function hasDocumentContent(document: DiagnosisDocumentStatus): boolean {
  if (document.content_text?.trim().length > 0) return true;
  if (document.parse_metadata?.pdf_analysis?.summary?.trim()) return true;
  return false;
}

function getParseFailureMessage(document: DiagnosisDocumentStatus): string {
  if (document.latest_async_job_error) return document.latest_async_job_error;
  if (document.last_error) return document.last_error;
  return '생활기록부 분석에 실패했습니다. 다른 파일로 다시 시도해 주세요.';
}

async function waitForDocumentParseResult(
  documentId: string,
  onPoll?: (document: DiagnosisDocumentStatus) => void,
): Promise<DiagnosisDocumentStatus> {
  const startedAt = Date.now();

  while (Date.now() - startedAt < PARSE_TIMEOUT_MS) {
    const document = await api.get<DiagnosisDocumentStatus>(`/api/v1/documents/${documentId}`);
    onPoll?.(document);
    if (PARSE_TERMINAL_STATUSES.has(document.status)) return document;
    await new Promise(resolve => window.setTimeout(resolve, PARSE_POLL_INTERVAL_MS));
  }

  throw new Error('문서 분석 시간이 예상보다 오래 걸리고 있어요. 잠시 후 다시 시도해 주세요.');
}

export function Diagnosis() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuthStore();
  const { goals, setGoals, submitGoals } = useOnboardingStore();
  const preselectedProjectId = searchParams.get('project_id')?.trim() || null;
  const autoLoadedProjectRef = useRef<string | null>(null);
  const autoSkipGoalStepRef = useRef(false);
  const diagnosisProcessKickoffRef = useRef<Set<string>>(new Set());
  const parseProcessKickoffRef = useRef<Set<string>>(new Set());

  const [step, setStep] = useState<DiagnosisStep>(() => {
    if (preselectedProjectId) return 'ANALYSING';
    // If user already has targets, default to UPLOAD step
    if (user?.target_university && user?.target_major) return 'UPLOAD';
    return 'GOALS';
  });
  const [goalList, setGoalList] = useState<Array<{ id: string; university: string; major: string }>>([]);
  const [isEditingGoals, setIsEditingGoals] = useState(false);
  const [univInput, setUnivInput] = useState('');
  const [currentUniv, setCurrentUniv] = useState('');
  const [currentMajor, setCurrentMajor] = useState('');

  const [projectId, setProjectId] = useState<string | null>(preselectedProjectId);
  const [isUploading, setIsUploading] = useState(false);
  const [diagnosisResult, setDiagnosisResult] = useState<DiagnosisResultPayload | null>(null);
  const [diagnosisRunId, setDiagnosisRunId] = useState<string | null>(null);
  const [diagnosisRun, setDiagnosisRun] = useState<DiagnosisRunResponse | null>(null);
  const [diagnosisJob, setDiagnosisJob] = useState<AsyncJobRead | null>(null);
  const [diagnosisError, setDiagnosisError] = useState<string | null>(null);
  const [isRetryingDiagnosis, setIsRetryingDiagnosis] = useState(false);
  const [flowError, setFlowError] = useState<string | null>(null);
  const [timingPhases, setTimingPhases] = useState<TimingPhaseMap>(() => createInitialTimingPhases());
  const useSynchronousApiJobs = shouldUseSynchronousApiJobs();
  const goalListRef = useRef(goalList);
  const currentMajorRef = useRef(currentMajor);

  const [isLoadingProject, setIsLoadingProject] = useState(false);

  const setTimingPhase = useCallback(
    (phase: TimingPhaseKey, updater: Partial<TimingPhaseState> | ((prev: TimingPhaseState) => TimingPhaseState)) => {
      setTimingPhases((prev) => {
        const current = prev[phase];
        const next = typeof updater === 'function' ? updater(current) : { ...current, ...updater };
        return { ...prev, [phase]: next };
      });
    },
    [],
  );

  const beginTimingPhase = useCallback((phase: TimingPhaseKey, note?: string) => {
    const now = Date.now();
    setTimingPhase(phase, {
      status: 'running',
      startedAt: now,
      finishedAt: null,
      note,
    });
  }, [setTimingPhase]);

  const finishTimingPhase = useCallback((phase: TimingPhaseKey, status: Exclude<TimingPhaseStatus, 'idle'>, note?: string) => {
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
      (Object.keys(next) as TimingPhaseKey[]).forEach((phase) => {
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

  useEffect(() => {
    goalListRef.current = goalList;
  }, [goalList]);

  useEffect(() => {
    currentMajorRef.current = currentMajor;
  }, [currentMajor]);

  const triggerInlineDiagnosisProcessing = useCallback(
    (jobId: string) => {
      if (!jobId) return;
      const kickoffCache = diagnosisProcessKickoffRef.current;
      if (kickoffCache.has(jobId)) return;
      kickoffCache.add(jobId);

      void api.post<AsyncJobRead>(`/api/v1/jobs/${jobId}/process`)
        .then((processed) => {
          setDiagnosisJob((previous) => (previous && previous.id !== processed.id ? previous : processed));
        })
        .catch(() => {
          // Allow a later retry kick if processing endpoint is temporarily unavailable.
          kickoffCache.delete(jobId);
        });
    },
    [],
  );

  const triggerInlineParseProcessing = useCallback(
    (document: DiagnosisDocumentStatus | null | undefined) => {
      if (!document) return;

      const jobId = document.latest_async_job_id;
      const jobStatus = (document.latest_async_job_status || '').toLowerCase();
      if (!jobId || (jobStatus !== 'queued' && jobStatus !== 'retrying')) return;

      const kickoffCache = parseProcessKickoffRef.current;
      if (kickoffCache.has(jobId)) return;
      kickoffCache.add(jobId);

      void api.post<AsyncJobRead>(`/api/v1/jobs/${jobId}/process`)
        .catch(() => {
          // Allow retrying a process kick if this call temporarily fails.
          kickoffCache.delete(jobId);
        });
    },
    [],
  );

  useEffect(() => {
    if (!user) return;

    const initial = buildRankedGoals(user, 6).map((goal, idx) => ({
      id: idx === 0 ? 'main' : `interest-${idx - 1}`,
      university: goal.university,
      major: goal.major,
    }));
    setGoalList(initial);

    // If we have a preselected project, try to load its state
    if (preselectedProjectId && !autoLoadedProjectRef.current) {
      autoLoadedProjectRef.current = preselectedProjectId;
      setIsLoadingProject(true);
      
      void api.get<any>(`/api/v1/projects/${preselectedProjectId}`)
        .then(async (project) => {
          // If project has goals, update our local list and potentially skip goals step
          if (project.target_university) {
            const projectGoals = [{ 
              id: 'main', 
              university: project.target_university, 
              major: project.target_major || '' 
            }];
            
            if (project.interest_universities?.length) {
              project.interest_universities.forEach((iu: string, idx: number) => {
                const match = iu.match(/(.+)\s*\((.+)\)/);
                if (match) {
                  projectGoals.push({ id: `interest-${idx}`, university: match[1].trim(), major: match[2].trim() });
                } else {
                  projectGoals.push({ id: `interest-${idx}`, university: iu.trim(), major: '' });
                }
              });
            }
            setGoalList(projectGoals);
            // Automatic skip to next step if project has goals and documents
            if (project.documents?.length > 0) {
              setStep('ANALYSING');
              return;
            }
          }

          // Check for existing diagnosis run
          if (project.latest_diagnosis_run_id) {
            setDiagnosisRunId(project.latest_diagnosis_run_id);
            setStep('ANALYSING');
          } else if (project.documents?.length) {
            setStep('ANALYSING');
            startDiagnosisForProject(preselectedProjectId);
          } else {
            setStep('UPLOAD');
          }
        })
        .catch((err) => {
          console.error("Failed to load project:", err);
          setStep('GOALS');
        })
        .finally(() => {
          setIsLoadingProject(false);
        });
    } else if (!autoSkipGoalStepRef.current && !preselectedProjectId && user.target_university) {
      // If user already has a target university set in profile, skip the goals selection step
      setStep('UPLOAD');
      autoSkipGoalStepRef.current = true;
    }
  }, [preselectedProjectId, user]);

  const handleAddGoal = () => {
    if (!currentUniv || !currentMajor || goalList.length >= 6) return;
    setGoalList(prev => [...prev, { id: crypto.randomUUID(), university: currentUniv, major: currentMajor }]);
    setCurrentUniv('');
    setCurrentMajor('');
    setUnivInput('');
  };

  const removeGoal = (id: string) => setGoalList(prev => prev.filter(goal => goal.id !== id));

  const saveGoals = async () => {
    if (!goalList.length) {
      toast.error('최소 1개의 목표를 설정해 주세요.');
      return;
    }

    const main = goalList[0];
    const others = goalList.slice(1).map(goal => `${goal.university} (${goal.major})`);
    const payload = {
      target_university: main.university,
      target_major: main.major,
      interest_universities: others,
      admission_type: goals.admission_type || '학생부종합',
    };

    setGoals(payload);

    const success = await submitGoals(payload);
    if (success) {
      setIsEditingGoals(false);
      toast.success('목표가 저장되었습니다.');
    }
  };

  const completeDiagnosis = useCallback(
    (run: DiagnosisRunResponse) => {
      const payload = mergeDiagnosisPayload(run);
      if (!payload) return false;
      if (run.async_job_id) {
        diagnosisProcessKickoffRef.current.delete(run.async_job_id);
      }

      finishTimingPhase('diagnosis', 'done', '진단 생성 완료');
      setProjectId(run.project_id);
      setDiagnosisRun(run);
      setDiagnosisResult(payload);
      setDiagnosisError(null);
      setFlowError(null);
      setStep('RESULT');
      setDiagnosisRunId(null);
      setIsUploading(false);

      const latestGoals = goalListRef.current;
      const primaryMajor = latestGoals[0]?.major || currentMajorRef.current || '';
      localStorage.setItem(
        DIAGNOSIS_STORAGE_KEY,
        JSON.stringify({
          major: primaryMajor,
          projectId: run.project_id,
          savedAt: new Date().toISOString(),
          diagnosis: {
            headline: payload.headline,
            strengths: payload.strengths,
            gaps: payload.gaps,
            risk_level: payload.risk_level,
            recommended_focus: payload.recommended_focus,
          },
        }),
      );

      return true;
    },
    [finishTimingPhase],
  );

  const syncDiagnosisRun = useCallback(
    async (runId: string) => {
      const run = await api.get<DiagnosisRunResponse>(`/api/v1/diagnosis/${runId}`);
      setDiagnosisRun(run);

      let job: AsyncJobRead | null = null;
      if (run.async_job_id) {
        try {
          job = await api.get<AsyncJobRead>(`/api/v1/jobs/${run.async_job_id}`);
        } catch {
          job = null;
        }
      }
      setDiagnosisJob(job);
      if (!job && run.async_job_id) {
        triggerInlineDiagnosisProcessing(run.async_job_id);
      }
      if (job?.status === 'succeeded' || job?.status === 'failed') {
        diagnosisProcessKickoffRef.current.delete(job.id);
      }
      if (job?.status === 'queued') {
        diagnosisProcessKickoffRef.current.delete(job.id);
        triggerInlineDiagnosisProcessing(job.id);
      }

      if (isDiagnosisComplete(run)) {
        const completed = completeDiagnosis(run);
        if (!completed) {
          const failureMessage = '진단 결과를 불러오지 못했어요. 다시 시도해 주세요.';
          finishTimingPhase('diagnosis', 'failed', failureMessage);
          setDiagnosisError(failureMessage);
          setFlowError(failureMessage);
          setStep('FAILED');
          setDiagnosisRunId(null);
          setIsUploading(false);
        }
        return true;
      }

      if (isDiagnosisFailed(run, job)) {
        const failureMessage = getDiagnosisFailureMessage(run, job);
        finishTimingPhase('diagnosis', 'failed', failureMessage);
        setDiagnosisError(failureMessage);
        setFlowError(failureMessage);
        setStep('FAILED');
        setDiagnosisRunId(null);
        setIsUploading(false);
        return true;
      }

      return false;
    },
    [completeDiagnosis, finishTimingPhase, triggerInlineDiagnosisProcessing],
  );

  useEffect(() => {
    if (!diagnosisRunId) return undefined;

    let cancelled = false;
    let timeoutId: number | undefined;

    const poll = async () => {
      try {
        const terminal = await syncDiagnosisRun(diagnosisRunId);
        if (!cancelled && !terminal) timeoutId = window.setTimeout(poll, 2000);
      } catch (error) {
        console.error('Polling failed', error);
        if (!cancelled) {
          const failureMessage = '진단 상태를 갱신하지 못했습니다.';
          finishTimingPhase('diagnosis', 'failed', failureMessage);
          setDiagnosisError(failureMessage);
          setFlowError(failureMessage);
          setStep('FAILED');
          setDiagnosisRunId(null);
          setIsUploading(false);
        }
      }
    };

    void poll();

    return () => {
      cancelled = true;
      if (timeoutId) window.clearTimeout(timeoutId);
    };
  }, [diagnosisRunId, finishTimingPhase, syncDiagnosisRun]);

  useEffect(() => {
    if (step !== 'RESULT') return undefined;
    if (!diagnosisRun?.id) return undefined;

    const normalizedReportStatus = (
      diagnosisRun.report_status ||
      diagnosisRun.report_async_job_status ||
      ''
    ).trim().toUpperCase();
    if (normalizedReportStatus === 'READY' || normalizedReportStatus === 'FAILED') return undefined;

    let cancelled = false;
    const pollReportProgress = async () => {
      try {
        const refreshed = await api.get<DiagnosisRunResponse>(`/api/v1/diagnosis/${diagnosisRun.id}`);
        if (cancelled) return;
        setDiagnosisRun((previous) => {
          if (!previous || previous.id !== refreshed.id) return previous;
          return refreshed;
        });
      } catch {
        // Keep showing the latest known state; manual regenerate is still available.
      }
    };

    void pollReportProgress();
    const timer = window.setInterval(() => {
      void pollReportProgress();
    }, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [diagnosisRun?.id, diagnosisRun?.report_async_job_status, diagnosisRun?.report_status, step]);

  const retryDiagnosis = useCallback(async () => {
    if (!diagnosisRun?.async_job_id || isRetryingDiagnosis) return;

    setIsRetryingDiagnosis(true);
    try {
      beginTimingPhase('diagnosis', '진단 재시도 진행 중');
      const retried = await api.post<AsyncJobRead>(`/api/v1/jobs/${diagnosisRun.async_job_id}/retry`);
      setDiagnosisJob(retried);
      setDiagnosisError(null);
      setFlowError(null);
      setStep('ANALYSING');

      if (useSynchronousApiJobs) {
        await api.post<AsyncJobRead>(`/api/v1/jobs/${retried.id}/process`);
        await syncDiagnosisRun(diagnosisRun.id);
        setDiagnosisRunId(null);
        toast.success('재시도를 즉시 처리했습니다.');
      } else {
        setDiagnosisRunId(diagnosisRun.id);
        triggerInlineDiagnosisProcessing(retried.id);
        toast.success('재시도를 요청했습니다.');
      }
    } catch (error) {
      console.error('Diagnosis retry failed:', error);
      finishTimingPhase('diagnosis', 'failed', '진단 재시도 요청 실패');
      toast.error('재시도 요청에 실패했습니다.');
    } finally {
      setIsRetryingDiagnosis(false);
    }
  }, [beginTimingPhase, diagnosisRun, finishTimingPhase, isRetryingDiagnosis, syncDiagnosisRun, triggerInlineDiagnosisProcessing, useSynchronousApiJobs]);

  const startDiagnosisForProject = useCallback(
    async (activeProjectId: string): Promise<boolean> => {
      const diagnosisUrl = useSynchronousApiJobs ? '/api/v1/diagnosis/run?wait_for_completion=true' : '/api/v1/diagnosis/run';
      const others = goalList.slice(1).map(goal => `${goal.university} (${goal.major})`);
      const run = await api.post<DiagnosisRunResponse>(diagnosisUrl, { 
        project_id: activeProjectId,
        interest_universities: others 
      });
      setProjectId(activeProjectId);
      setDiagnosisRun(run);
      setDiagnosisJob(null);

      if (isDiagnosisComplete(run)) {
        const completed = completeDiagnosis(run);
        if (!completed) {
          const failureMessage = '진단 결과를 불러오지 못했어요. 다시 시도해 주세요.';
          finishTimingPhase('diagnosis', 'failed', failureMessage);
          setDiagnosisError(failureMessage);
          setFlowError(failureMessage);
          setStep('FAILED');
          setDiagnosisRunId(null);
          setIsUploading(false);
          return false;
        }
        return true;
      }

      if (isDiagnosisFailed(run, null)) {
        const runFailure = getDiagnosisFailureMessage(run, null);
        finishTimingPhase('diagnosis', 'failed', runFailure);
        setDiagnosisError(runFailure);
        setFlowError(runFailure);
        setStep('FAILED');
        setDiagnosisRunId(null);
        setIsUploading(false);
        return false;
      }

      setDiagnosisRunId(run.id);
      if (run.async_job_id) {
        triggerInlineDiagnosisProcessing(run.async_job_id);
      }
      return true;
    },
    [completeDiagnosis, finishTimingPhase, goalList, triggerInlineDiagnosisProcessing, useSynchronousApiJobs],
  );

  const completeDiagnosisRef = useRef(completeDiagnosis);
  const failRunningTimingPhasesRef = useRef(failRunningTimingPhases);
  const startDiagnosisForProjectRef = useRef(startDiagnosisForProject);
  const triggerInlineDiagnosisProcessingRef = useRef(triggerInlineDiagnosisProcessing);

  useEffect(() => {
    completeDiagnosisRef.current = completeDiagnosis;
  }, [completeDiagnosis]);

  useEffect(() => {
    failRunningTimingPhasesRef.current = failRunningTimingPhases;
  }, [failRunningTimingPhases]);

  useEffect(() => {
    startDiagnosisForProjectRef.current = startDiagnosisForProject;
  }, [startDiagnosisForProject]);

  useEffect(() => {
    triggerInlineDiagnosisProcessingRef.current = triggerInlineDiagnosisProcessing;
  }, [triggerInlineDiagnosisProcessing]);

  useEffect(() => {
    if (!preselectedProjectId) return;
    if (autoLoadedProjectRef.current === preselectedProjectId) return;
    autoLoadedProjectRef.current = preselectedProjectId;

    let cancelled = false;

    const hydrateFromRecordUpload = async () => {
      const loadingId = toast.loading('업로드한 기록으로 진단 결과를 확인하고 있어요..');
      const now = Date.now();

      setProjectId(preselectedProjectId);
      setDiagnosisResult(null);
      setDiagnosisRun(null);
      setDiagnosisJob(null);
      setDiagnosisRunId(null);
      setDiagnosisError(null);
      setFlowError(null);
      setStep('ANALYSING');
      setIsUploading(true);
      setTimingPhases({
        upload: { status: 'done', startedAt: now, finishedAt: now, note: '기록 업로드 완료' },
        parse: { status: 'running', startedAt: now, finishedAt: null, note: '문서 내용을 꼼꼼하게 분석 중' },
        diagnosis: { status: 'idle', startedAt: null, finishedAt: null, note: '진단 대기 중' },
      });

      try {
        let latestRun: DiagnosisRunResponse | null = null;
        try {
          latestRun = await api.get<DiagnosisRunResponse>(`/api/v1/diagnosis/project/${preselectedProjectId}/latest`);
        } catch (latestError: any) {
          if (latestError?.response?.status !== 404) throw latestError;
        }

        if (cancelled) return;

        if (latestRun && !isDiagnosisFailed(latestRun, null)) {
          setDiagnosisRun(latestRun);

          if (isDiagnosisComplete(latestRun)) {
            const loaded = completeDiagnosisRef.current(latestRun);
            if (loaded) {
              toast.success('기존 진단 결과를 바로 불러왔어요.', { id: loadingId });
              return;
            }
          } else {
            setDiagnosisRunId(latestRun.id);
            if (latestRun.async_job_id) {
              triggerInlineDiagnosisProcessingRef.current(latestRun.async_job_id);
            }
            beginTimingPhase('diagnosis', '진단 진행 중');
            toast.success('진행 중이던 진단 작업을 이어 보여드릴게요.', { id: loadingId });
            return;
          }
        }

        beginTimingPhase('diagnosis', '진단 생성 진행 중');
        const started = await startDiagnosisForProjectRef.current(preselectedProjectId);
        if (!cancelled && started) {
          toast.success('업로드한 기록으로 진단을 시작했어요.', { id: loadingId });
        }
      } catch (error: any) {
        if (cancelled) return;
        const failureMessage = getApiErrorMessage(error, '저장된 업로드 기록으로 진단을 시작하지 못했어요.');
        failRunningTimingPhasesRef.current(failureMessage);
        setDiagnosisError(failureMessage);
        setFlowError(failureMessage);
        setStep('FAILED');
        setIsUploading(false);
        toast.error(failureMessage, { id: loadingId });
      }
    };

    void hydrateFromRecordUpload();

    return () => {
      cancelled = true;
    };
  }, [beginTimingPhase, preselectedProjectId]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;
      if (file.size > MAX_UPLOAD_BYTES) {
        toast.error('파일 용량이 50MB를 초과하여 업로드할 수 없습니다.');
        return;
      }

      setDiagnosisResult(null);
      setDiagnosisRun(null);
      setDiagnosisJob(null);
      setDiagnosisRunId(null);
      setDiagnosisError(null);
      setFlowError(null);
      resetTimingPhases();
      setIsUploading(true);
      const loadingId = toast.loading('PDF 업로드와 진단 준비를 진행 중입니다...');

      try {
        beginTimingPhase('upload', '파일 업로드 진행 중');
        const formData = new FormData();
        formData.append('file', file);
        const mainGoal = goalList[0];
        if (mainGoal) {
          formData.append('target_university', mainGoal.university);
          formData.append('target_major', mainGoal.major);
          formData.append('title', `${mainGoal.university} ${mainGoal.major} 진단`);
        }

        const uploadRes = await api.post<{ project_id: string; id: string }>('/api/v1/documents/upload', formData);
        setProjectId(uploadRes.project_id);
        finishTimingPhase('upload', 'done', `업로드 완료 (${(file.size / (1024 * 1024)).toFixed(1)}MB)`);

        beginTimingPhase('parse', '기록 내용을 꼼꼼히 읽고 있어요');
        setStep('ANALYSING');
        const parseUrl = useSynchronousApiJobs
          ? `/api/v1/documents/${uploadRes.id}/parse?wait_for_completion=true`
          : `/api/v1/documents/${uploadRes.id}/parse`;
        const parseStarted = await api.post<DiagnosisDocumentStatus>(parseUrl);
        triggerInlineParseProcessing(parseStarted);
        const parsedDocument = PARSE_TERMINAL_STATUSES.has(parseStarted.status)
          ? parseStarted
          : await waitForDocumentParseResult(uploadRes.id, triggerInlineParseProcessing);
        if (parsedDocument.latest_async_job_id && PARSE_TERMINAL_STATUSES.has(parsedDocument.status)) {
          parseProcessKickoffRef.current.delete(parsedDocument.latest_async_job_id);
        }

        if (!PARSE_SUCCESS_STATUSES.has(parsedDocument.status)) {
          const parseError = getParseFailureMessage(parsedDocument);
          finishTimingPhase('parse', 'failed', parseError);
          setDiagnosisError(parseError);
          setFlowError(parseError);
          setStep('FAILED');
          setIsUploading(false);
          toast.error(parseError, { id: loadingId });
          return;
        }

        if (!hasDocumentContent(parsedDocument)) {
          const emptyContentError = 'PDF에서 진단 가능한 텍스트를 찾지 못했습니다. OCR 품질이 더 좋은 파일로 다시 시도해 주세요.';
          finishTimingPhase('parse', 'failed', emptyContentError);
          setDiagnosisError(emptyContentError);
          setFlowError(emptyContentError);
          setStep('FAILED');
          setIsUploading(false);
          toast.error(emptyContentError, { id: loadingId });
          return;
        }

        const parseNote = parsedDocument.page_count ? `분석 완료 (${parsedDocument.page_count}쪽)` : '분석 완료';
        finishTimingPhase('parse', 'done', parseNote);
        beginTimingPhase('diagnosis', '진단 생성 진행 중');

        await startDiagnosisForProject(uploadRes.project_id);

        toast.success('진단 실행이 시작되었습니다.', { id: loadingId });
      } catch (error: any) {
        console.error('Diagnosis flow failed:', error);
        const failureMessage = getApiErrorMessage(error, '진단 실행에 실패했습니다. 잠시 후 다시 시도해 주세요.');
        failRunningTimingPhasesRef.current(failureMessage);
        setDiagnosisError(failureMessage);
        setFlowError(failureMessage);
        setStep('FAILED');
        toast.error(failureMessage, { id: loadingId });
        setIsUploading(false);
      }
    },
    [
      beginTimingPhase,
      failRunningTimingPhases,
      finishTimingPhase,
      goalList,
      resetTimingPhases,
      startDiagnosisForProject,
      triggerInlineParseProcessing,
      useSynchronousApiJobs,
    ],
  );

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    disabled: isUploading,
    noClick: true,
    noKeyboard: true,
    useFsAccessApi: false,
  });

  const handleOpenFileDialog = useCallback(() => {
    if (isUploading) return;
    open();
  }, [isUploading, open]);

  const handleDropzoneKeyDown = useCallback((event: React.KeyboardEvent<HTMLDivElement>) => {
    if (isUploading) return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      open();
    }
  }, [isUploading, open]);

  const evidenceCitations = diagnosisResult?.citations ?? diagnosisRun?.citations ?? [];
  const reviewRequired = diagnosisResult?.review_required ?? diagnosisRun?.review_required ?? false;
  const responseTraceId = diagnosisResult?.response_trace_id ?? diagnosisRun?.response_trace_id ?? null;
  const univPreviewName = (currentUniv || univInput).trim();
  const deliveryResolution = resolveDiagnosisDeliveryState(diagnosisRun, diagnosisJob);
  const hasSecondaryInsights = Boolean(
    diagnosisResult?.risks?.length ||
      diagnosisResult?.recommended_topics?.length ||
      diagnosisResult?.action_plan?.length,
  );
  const hasAdvancedDiagnostics = Boolean(
    diagnosisResult?.document_quality ||
      diagnosisResult?.section_analysis?.length ||
      diagnosisResult?.admission_axes?.length ||
      diagnosisResult?.claims?.length ||
      evidenceCitations.length ||
      reviewRequired ||
      responseTraceId ||
      diagnosisRun?.policy_flags?.length,
  );
  const shouldShowProgressRail = step !== 'RESULT';

  const stepItems: Array<{ id: string; label: string; description: string; state: 'done' | 'active' | 'pending' | 'error' }> = [
    {
      id: 'goals',
      label: '목표 설정',
      description: '지원 목표 확정',
      state: step === 'GOALS' ? 'active' : ['UPLOAD', 'ANALYSING', 'RESULT', 'FAILED'].includes(step) ? 'done' : 'pending',
    },
    {
      id: 'upload',
      label: '기록 업로드',
      description: '학생부 PDF 제출',
      state: step === 'UPLOAD' ? 'active' : ['ANALYSING', 'RESULT', 'FAILED'].includes(step) ? 'done' : 'pending',
    },
    {
      id: 'analysis',
      label: '진단 실행',
      description: '근거 기반 분석',
      state: step === 'ANALYSING' ? 'active' : step === 'RESULT' ? 'done' : step === 'FAILED' ? 'error' : 'pending',
    },
    {
      id: 'result',
      label: '결과 검토',
      description: '워크숍 진입 판단',
      state: step === 'RESULT' ? 'active' : step === 'FAILED' ? 'error' : 'pending',
    },
  ];

  const headerTitle =
    step === 'GOALS' ? '진단 목표 확인' :
    step === 'UPLOAD' ? '생활기록부 등록' :
    step === 'ANALYSING' ? '기록 정밀 분석 중' :
    step === 'RESULT' ? 'AI 정밀 진단 보고서' :
    '확인 필요';

  const headerDescription =
    step === 'GOALS' ? '목표 대학교와 학과를 기반으로 입시 경쟁력을 정밀하게 분석합니다.' :
    step === 'UPLOAD' ? '생활기록부 PDF를 등록하시면 개인정보 보호 처리 후 AI 분석을 시작합니다.' :
    step === 'ANALYSING' ? '나의 기록을 꼼꼼히 읽고 지원 전략에 필요한 합격 근거를 도출하고 있습니다.' :
    step === 'RESULT' ? '생기부의 강점, 보완점, 그리고 합격을 위한 구체적인 액션 플랜입니다.' :
    '문제가 발생했습니다. 다시 시도해 주세요.';

  const timingPhaseItems = [
    { id: 'upload', label: '업로드', expectedSeconds: 20, ...timingPhases.upload },
    { id: 'parse', label: '기록 분석', expectedSeconds: 90, ...timingPhases.parse },
    { id: 'diagnosis', label: '정밀 진단', expectedSeconds: 120, ...timingPhases.diagnosis },
  ];
  const shouldShowTimingDashboard = timingPhaseItems.some((phase) => phase.startedAt !== null);

  return (
    <div className="mx-auto max-w-6xl space-y-8 py-8 animate-in fade-in duration-700">
      <div className="relative overflow-hidden rounded-[2.5rem] bg-gradient-to-br from-[#004aad] to-[#0070f3] p-8 md:p-12 shadow-2xl shadow-blue-500/20">
        <div className="absolute -right-24 -top-24 h-96 w-96 rounded-full bg-white/10 blur-3xl animate-pulse" />
        <div className="absolute -bottom-24 -left-24 h-96 w-96 rounded-full bg-cyan-400/20 blur-3xl" />
        
        <div className="relative z-10 space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-1.5 backdrop-blur-md ring-1 ring-white/20">
            <Sparkles size={14} className="text-cyan-300" />
            <span className="text-sm font-bold tracking-tight text-cyan-50">PREMIUM AI ANALYSIS</span>
          </div>
          <h1 className="text-4xl font-black tracking-tight text-white md:text-5xl lg:leading-[1.15]">
            {headerTitle}
          </h1>
          <p className="max-w-2xl text-lg font-medium leading-relaxed text-blue-100/80">
            {headerDescription}
          </p>
        </div>
      </div>

      {shouldShowProgressRail ? (
        <div className="px-4">
          <StepIndicator items={stepItems} />
        </div>
      ) : null}

      {shouldShowProgressRail && shouldShowTimingDashboard ? (
        <div className="animate-in slide-in-from-top-4 duration-500">
          <ProcessTimingDashboard
            phases={timingPhaseItems}
            title="실시간 진단 현황"
            description="데이터 마스킹과 정밀 분석이 실시간으로 진행 중입니다"
          />
        </div>
      ) : null}

      <AnimatePresence mode="wait">
        {step === 'GOALS' ? (
          <motion.div key="goals" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }} className="space-y-6">
            <SectionCard
              title="목표 대학 및 학과 선택"
              description="설정한 목표를 바탕으로 생기부를 분석합니다. 대학별 인재상에 맞춰 정밀하게 진단합니다."
              className="border-none bg-white/60 shadow-xl backdrop-blur-2xl ring-1 ring-white/50"
              actions={
                !isEditingGoals ? (
                  <SecondaryButton data-testid="diagnosis-edit-goals" onClick={() => setIsEditingGoals(true)}>
                    설정 수정하기
                  </SecondaryButton>
                ) : null
              }
            >
              {isEditingGoals ? (
                <div className="grid gap-8 lg:grid-cols-2">
                  <SurfaceCard tone="muted" className="border-none bg-slate-50 shadow-inner">
                    <div className="relative">
                      <label className="mb-2 block text-xs font-bold uppercase tracking-[0.14em] text-slate-500">목표 대학교 검색</label>
                      <input
                        data-testid="diagnosis-university-search"
                        type="text"
                        value={univInput}
                        onChange={event => setUnivInput(event.target.value)}
                        placeholder="예: 서울대학교"
                        className="h-12 w-full rounded-2xl border border-slate-200 bg-white px-4 pr-12 text-sm font-semibold shadow-sm transition-all outline-none focus:border-[#004aad] focus:ring-4 focus:ring-[#004aad]/10"
                      />
                      {univPreviewName.length >= 2 ? (
                        <UniversityLogo
                          universityName={univPreviewName}
                          className="pointer-events-none absolute right-3 top-[34px] h-8 w-8 rounded-lg bg-white object-contain p-1 shadow-sm"
                          fallbackClassName="border border-slate-100"
                        />
                      ) : null}
                      {univInput ? (
                        <div className="absolute left-0 right-0 top-full z-20 mt-2 max-h-60 overflow-auto rounded-2xl border border-slate-200 bg-white p-2 shadow-2xl backdrop-blur-xl">
                          {searchUniversities(univInput, { excludeNames: goalList.map(goal => goal.university) }).map((suggestion, index) => (
                            <button
                              key={suggestion.label}
                              type="button"
                              data-testid={`diagnosis-university-option-${index}`}
                              onClick={() => {
                                setCurrentUniv(suggestion.label);
                                setUnivInput('');
                              }}
                              className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left transition-colors hover:bg-[#004aad]/5"
                            >
                              <UniversityLogo universityName={suggestion.label} className="h-6 w-6 rounded-md bg-white object-contain p-0.5" />
                              <span className="text-sm font-bold text-slate-700">{suggestion.label}</span>
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </div>

                    {currentUniv ? (
                      <div className="mt-8 space-y-5 rounded-3xl border border-[#004aad]/10 bg-gradient-to-br from-[#004aad]/5 to-transparent p-6">
                        <div className="flex items-center justify-between gap-2 border-b border-[#004aad]/10 pb-4">
                          <div className="flex items-center gap-3">
                            <UniversityLogo
                              universityName={currentUniv}
                              className="h-10 w-10 rounded-xl bg-white object-contain p-1 shadow-md"
                            />
                            <h4 className="text-lg font-black text-slate-900">{currentUniv}</h4>
                          </div>
                          <button type="button" onClick={() => setCurrentUniv('')} className="rounded-xl p-2 text-slate-400 hover:bg-white hover:text-red-500">
                            <Trash2 size={18} />
                          </button>
                        </div>
                        <CatalogAutocompleteInput
                          label="희망 학과"
                          value={currentMajor}
                          onChange={setCurrentMajor}
                          placeholder="학과명을 직접 입력하거나 검색하세요"
                          suggestions={searchMajors(currentMajor, currentUniv, 15)}
                          onSelect={item => setCurrentMajor(item.label)}
                        />
                        <PrimaryButton
                          data-testid="diagnosis-add-goal"
                          onClick={handleAddGoal}
                          disabled={!currentUniv || currentMajor.length < 2 || goalList.length >= 6}
                          fullWidth
                          size="lg"
                          className="shadow-lg shadow-blue-500/10"
                        >
                          <Plus size={18} />
                          목표 리스트에 추가
                        </PrimaryButton>
                      </div>
                    ) : null}
                  </SurfaceCard>

                  <div className="space-y-3">
                    <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">나의 선택 리스트 ({goalList.length}/6)</p>
                    <AnimatePresence initial={false}>
                      {goalList.map((goal, index) => (
                        <motion.div
                          key={goal.id}
                          initial={{ opacity: 0, scale: 0.95 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.95 }}
                        >
                          <SurfaceCard padding="sm" className="flex items-center justify-between gap-4 border-slate-100 shadow-sm transition-all hover:border-[#004aad]/20">
                            <div className="flex min-w-0 items-center gap-3">
                              <UniversityLogo
                                universityName={goal.university}
                                className="h-10 w-10 rounded-xl bg-slate-50 object-contain p-1.5"
                              />
                              <div className="min-w-0">
                                <p className="truncate text-sm font-black text-slate-900">{goal.university}</p>
                                <p className="truncate text-xs font-bold text-slate-500">{goal.major}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              {index === 0 ? (
                                <div className="rounded-full bg-blue-100 px-2.5 py-1 text-[10px] font-black text-[#004aad]">MAIN</div>
                              ) : null}
                              <button type="button" onClick={() => removeGoal(goal.id)} className="rounded-lg p-2 text-slate-300 hover:bg-red-50 hover:text-red-500">
                                <Trash2 size={16} />
                              </button>
                            </div>
                          </SurfaceCard>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                </div>
              ) : goalList.length ? (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {goalList.map((goal, index) => (
                    <div key={goal.id} className="group relative overflow-hidden rounded-3xl border border-slate-100 bg-slate-50/50 p-5 transition-all hover:bg-white hover:shadow-xl hover:shadow-blue-500/5">
                      <div className="mb-4 flex items-center justify-between">
                        <div className={`h-10 w-10 rounded-2xl p-1.5 shadow-sm bg-white`}>
                          <UniversityLogo universityName={goal.university} className="h-full w-full object-contain" />
                        </div>
                        {index === 0 ? (
                          <span className="rounded-full bg-blue-600 px-3 py-1 text-[10px] font-black text-white shadow-lg shadow-blue-500/20">대표 목표</span>
                        ) : (
                          <span className="text-[10px] font-bold text-slate-400">목표 {index + 1}</span>
                        )}
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-base font-black text-slate-900 group-hover:text-[#004aad] transition-colors">{goal.university}</p>
                        <p className="mt-0.5 truncate text-sm font-bold text-slate-500">{goal.major}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title="설정한 목표가 없습니다" description="나의 입시 전략을 구축할 목표 대학을 선택해 주세요." />
              )}
            </SectionCard>

            {isEditingGoals ? (
              <div className="flex items-center justify-end gap-3">
                <SecondaryButton className="bg-white border-slate-200" onClick={() => {
                  setIsEditingGoals(false);
                  // Refresh goal list to state from onboarding store if canceled
                  if (user) {
                    const initial = buildRankedGoals(user, 6).map((goal, idx) => ({
                      id: idx === 0 ? 'main' : `interest-${idx - 1}`,
                      university: goal.university,
                      major: goal.major,
                    }));
                    setGoalList(initial);
                  }
                }}>변경 취소</SecondaryButton>
                <PrimaryButton data-testid="diagnosis-save-goals" size="lg" onClick={saveGoals}>
                  설정 완료
                </PrimaryButton>
              </div>
            ) : goalList.length > 0 ? (
              <div className="flex flex-col items-center gap-6 pt-4">
                <div className="inline-flex items-center gap-3 rounded-2xl bg-[#004aad]/5 px-6 py-3 text-sm font-bold text-[#004aad]">
                  <CheckCircle2 size={20} className="text-[#004aad]" />
                  <span>{goalList.length}개의 목표가 성공적으로 설정되었습니다.</span>
                </div>
                <PrimaryButton data-testid="diagnosis-goals-continue" onClick={() => setStep('UPLOAD')} size="lg" className="h-14 px-10 text-lg shadow-2xl shadow-blue-500/20">
                  다음: 생기부 등록하기
                  <ArrowRight size={22} className="ml-2" />
                </PrimaryButton>
              </div>
            ) : null}
          </motion.div>
        ) : null}

        {step === 'UPLOAD' ? (
          <motion.div key="upload" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }}>
            <SectionCard
              title="생활기록부 PDF 등록"
              description="생기부 1개(최대 50MB)를 등록하시면 개인정보 보호 처리 후 AI가 꼼꼼히 읽어봅니다."
              className="overflow-hidden border-none bg-white/60 shadow-xl backdrop-blur-2xl ring-1 ring-white/50"
              actions={
                <SecondaryButton 
                  size="sm" 
                  onClick={() => setStep('GOALS')}
                  className="bg-white/50 border-white/50 backdrop-blur-sm"
                >
                  <Settings2 size={14} className="mr-1.5" />
                  목표 대학 수정
                </SecondaryButton>
              }
            >
              <div className="grid gap-3 rounded-2xl bg-blue-50/50 p-6 sm:grid-cols-3 ring-1 ring-blue-100">
                <div className="flex flex-col gap-1 items-center text-center">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#004aad] text-xs font-bold text-white shadow-lg shadow-blue-500/20">1</div>
                  <p className="text-sm font-black text-slate-800">기록 등록</p>
                </div>
                <div className="flex flex-col gap-1 items-center text-center">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-xs font-bold text-slate-500">2</div>
                  <p className="text-sm font-bold text-slate-400">정밀 분석</p>
                </div>
                <div className="flex flex-col gap-1 items-center text-center">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-xs font-bold text-slate-500">3</div>
                  <p className="text-sm font-bold text-slate-400">결과 확인</p>
                </div>
              </div>

              <div
                {...getRootProps({
                  onClick: handleOpenFileDialog,
                  onKeyDown: handleDropzoneKeyDown,
                })}
                className={`group relative mt-6 cursor-pointer overflow-hidden rounded-[2rem] border-2 border-dashed transition-all duration-300 ${
                  isDragActive 
                    ? 'border-[#004aad] bg-[#004aad]/5 scale-[0.99]' 
                    : 'border-slate-200 bg-white hover:border-[#004aad]/40 hover:shadow-2xl hover:shadow-blue-500/10'
                } ${isUploading ? 'pointer-events-none opacity-60' : ''}`}
              >
                <input data-testid="diagnosis-upload-input" {...getInputProps()} />
                
                <div className="flex flex-col items-center px-6 py-12 text-center sm:py-20">
                  <div className="relative mb-8">
                    <div className="absolute inset-0 animate-ping rounded-full bg-blue-400 opacity-20"></div>
                    <div className="relative flex h-24 w-24 items-center justify-center rounded-3xl bg-gradient-to-br from-[#004aad] to-[#0070f3] text-white shadow-lg shadow-blue-500/20">
                      {isUploading ? (
                        <div className="w-12">
                          <div className="h-2 overflow-hidden rounded-full bg-white/20">
                            <motion.div
                              className="h-full rounded-full bg-white"
                              animate={{ x: ['-100%', '100%'] }}
                              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                            />
                          </div>
                        </div>
                      ) : (
                        <FileUp size={42} className="transition-transform duration-300 group-hover:-translate-y-1" />
                      )}
                    </div>
                  </div>

                  <h3 className="text-2xl font-black tracking-tight text-slate-900 sm:text-3xl">
                    생활기록부를 <span className="text-[#004aad]">이곳에 놓아주세요</span>
                  </h3>
                  <p className="mt-4 max-w-md text-lg font-medium text-slate-500 leading-relaxed">
                    파일을 드래그하거나 버튼을 클릭하여 업로드하면 <br className="hidden sm:block" />
                    즉시 AI 맞춤 진단이 시작됩니다.
                  </p>

                  <button
                    type="button"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      handleOpenFileDialog();
                    }}
                    disabled={isUploading}
                    className="mt-10 flex items-center gap-3 rounded-2xl bg-slate-900 px-8 py-4 text-base font-bold text-white shadow-xl shadow-slate-200 ring-offset-2 transition-all hover:bg-slate-800 hover:ring-2 hover:ring-slate-900 active:scale-95 disabled:opacity-50"
                  >
                    <Plus size={20} />
                    컴퓨터에서 파일 찾기
                  </button>
                </div>
              </div>

              {flowError ? (
                <div className="mt-6">
                  <WorkflowNotice tone="danger" title="작업 중 오류 발생" description={flowError} />
                </div>
              ) : null}
            </SectionCard>
          </motion.div>
        ) : null}

        {step === 'ANALYSING' ? (
          <motion.div key="analysing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
            <WorkflowNotice
              tone="loading"
              title="학생부 기록을 꼼꼼하게 분석하고 있습니다"
              description="내용 분석이 끝나면 자동으로 진단 단계로 넘어가며, 페이지를 유지하면 상태가 자동 갱신됩니다"
            />
            <AsyncJobStatusCard job={diagnosisJob} runStatus={diagnosisRun?.status} errorMessage={diagnosisRun?.error_message} />
          </motion.div>
        ) : null}

        {step === 'FAILED' ? (
          <motion.div key="failed" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-6">
            <WorkflowNotice tone="danger" title="진단 실행에 실패했습니다" description={flowError || diagnosisError || '작업 상태를 확인하고 다시 시도해 주세요.'} />

            <AsyncJobStatusCard
              job={diagnosisJob}
              runStatus={diagnosisRun?.status}
              errorMessage={diagnosisError}
              onRetry={diagnosisJob?.status === 'failed' ? retryDiagnosis : null}
              isRetrying={isRetryingDiagnosis}
            />

            <div className="flex flex-wrap items-center justify-center gap-2">
              <SecondaryButton
                onClick={() => {
                  setStep('UPLOAD');
                  setFlowError(null);
                  setDiagnosisError(null);
                }}
              >
                업로드로 돌아가기
              </SecondaryButton>
              {diagnosisJob?.status === 'failed' ? (
                <PrimaryButton onClick={retryDiagnosis} disabled={isRetryingDiagnosis}>
                  {isRetryingDiagnosis ? '재시도 중...' : '진단 재시도'}
                </PrimaryButton>
              ) : null}
            </div>
          </motion.div>
        ) : null}

        {step === 'RESULT' && diagnosisResult ? (
          <motion.div key="result" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            <SectionCard
              title={diagnosisResult.headline}
              description="나의 입시 경쟁력을 요약한 AI 종합 진정 분석 리포트입니다."
              eyebrow="AI 진단 리포트"
              data-testid="diagnosis-result-panel"
              className="border-none bg-white shadow-2xl ring-1 ring-slate-200/50"
              actions={
                <div className="flex flex-wrap items-center gap-2">
                  <div className={`flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-black shadow-lg ${
                    diagnosisResult.risk_level === 'safe' 
                      ? 'bg-emerald-500 text-white shadow-emerald-500/20' 
                      : diagnosisResult.risk_level === 'warning' 
                        ? 'bg-amber-500 text-white shadow-amber-500/20' 
                        : 'bg-rose-500 text-white shadow-rose-500/20'
                  }`}>
                    {formatRiskLevel(diagnosisResult.risk_level)}
                  </div>
                </div>
              }
            >
              {diagnosisResult.overview ? (
                <div className="mb-8 rounded-3xl bg-slate-50 p-6 sm:p-8">
                  <p className="text-lg font-bold leading-relaxed text-slate-700">
                    <span className="mb-2 block text-xs font-black uppercase tracking-widest text-slate-400">종합 분석 의견</span>
                    {diagnosisResult.overview}
                  </p>
                </div>
              ) : null}

              <div className="grid gap-6 md:grid-cols-2">
                <SurfaceCard className="border-none bg-emerald-50/50 p-6 ring-1 ring-emerald-100">
                  <div className="mb-4 flex items-center gap-2 text-emerald-700">
                    <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-500 text-white shadow-lg shadow-emerald-500/20">
                      <CheckCircle2 size={18} />
                    </div>
                    <span className="text-lg font-black italic">핵심 강점</span>
                    <span className="text-sm font-bold opacity-60">나의 생기부 강점</span>
                  </div>
                  <ul className="space-y-3">
                    {diagnosisResult.strengths.map((item, index) => (
                      <li key={index} className="flex gap-3 text-base font-bold leading-relaxed text-slate-700">
                        <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </SurfaceCard>

                <SurfaceCard className="border-none bg-rose-50/50 p-6 ring-1 ring-rose-100">
                  <div className="mb-4 flex items-center gap-2 text-rose-700">
                    <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-rose-500 text-white shadow-lg shadow-rose-500/20">
                      <AlertTriangle size={18} />
                    </div>
                    <span className="text-lg font-black italic">보완 포인트</span>
                    <span className="text-sm font-bold opacity-60">보완이 필요한 부분</span>
                  </div>
                  <ul className="space-y-3">
                    {(diagnosisResult.detailed_gaps?.length
                      ? diagnosisResult.detailed_gaps.map(gap => `${gap.title}: ${gap.description}`)
                      : diagnosisResult.gaps
                    ).map((item, index) => (
                      <li key={index} className="flex gap-3 text-base font-bold leading-relaxed text-slate-700">
                        <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-rose-400" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </SurfaceCard>
              </div>

              {diagnosisResult.next_actions?.length || diagnosisResult.recommended_focus ? (
                <div className="mt-8 rounded-[2rem] bg-slate-900 p-8 text-white shadow-2xl">
                  <div className="mb-6 flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/10 text-white">
                      <Zap size={20} fill="currentColor" />
                    </div>
                    <div>
                      <h4 className="text-lg font-black">실행 과제</h4>
                      <p className="text-sm font-bold text-slate-400">합격을 위한 향후 액션 플랜</p>
                    </div>
                  </div>

                  <div className="grid gap-8 lg:grid-cols-2">
                    {diagnosisResult.next_actions?.length ? (
                      <div className="space-y-4">
                        <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">주요 실천 과제</p>
                        <ul className="space-y-3">
                          {diagnosisResult.next_actions.map((action, i) => (
                            <li key={i} className="flex gap-3 text-base font-bold text-slate-100">
                              <span className="mt-2.5 flex h-1 w-1 shrink-0 rounded-full bg-blue-400" />
                              {action}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}

                    {diagnosisResult.recommended_focus ? (
                      <div className="space-y-4 border-l border-white/10 pl-8">
                        <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">추천 집중 영역</p>
                        <p className="text-lg font-bold leading-relaxed text-blue-100">
                          {diagnosisResult.recommended_focus}
                        </p>
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </SectionCard>

            {hasSecondaryInsights ? (
              <SectionCard
                title="상세 진단 결과"
                description="기본 요약 외에 AI가 분석한 추가 인사이트를 확인해 보세요."
                eyebrow="상세 분석"
                collapsible
                defaultCollapsed
              >
                {diagnosisResult.risks?.length ? (
                  <SurfaceCard tone="muted" padding="sm" className="border border-amber-200 bg-amber-50/70">
                    <p className="mb-2 text-xs font-bold uppercase tracking-[0.14em] text-amber-700">리스크</p>
                    <ul className="space-y-1.5">
                      {diagnosisResult.risks.map((risk) => (
                        <li key={risk} className="text-sm font-medium leading-6 text-amber-900">
                          • {risk}
                        </li>
                      ))}
                    </ul>
                  </SurfaceCard>
                ) : null}

                {diagnosisResult.recommended_topics?.length ? (
                  <SurfaceCard tone="muted" padding="sm">
                    <p className="mb-2 text-xs font-bold uppercase tracking-[0.14em] text-slate-400">추천 주제</p>
                    <div className="flex flex-wrap gap-2">
                      {diagnosisResult.recommended_topics.map((topic) => (
                        <StatusBadge key={topic} status="neutral">
                          {topic}
                        </StatusBadge>
                      ))}
                    </div>
                  </SurfaceCard>
                ) : null}

                {diagnosisResult.action_plan?.length ? (
                  <div className="space-y-2">
                    <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">권장 액션 플랜</p>
                    <div className="grid gap-3 md:grid-cols-2">
                      {diagnosisResult.action_plan.map((quest, index) => (
                        <SurfaceCard key={`${quest.title}-${index}`} padding="sm">
                          <div className="mb-2 flex items-center justify-between gap-2">
                            <p className="text-sm font-bold text-slate-800">{quest.title}</p>
                            <StatusBadge status={quest.priority === 'high' ? 'danger' : quest.priority === 'medium' ? 'warning' : 'neutral'}>
                              {quest.priority === 'high' ? '높음' : quest.priority === 'medium' ? '보통' : '낮음'}
                            </StatusBadge>
                          </div>
                          <p className="text-base font-medium leading-7 text-slate-600">{quest.description}</p>
                        </SurfaceCard>
                      ))}
                    </div>
                  </div>
                ) : null}
              </SectionCard>
            ) : null}

            {diagnosisRun?.id && projectId ? (
              <DiagnosisGuidedChoicePanel
                diagnosisRunId={diagnosisRun.id}
                projectId={projectId}
                diagnosis={diagnosisResult}
                useSynchronousApiJobs={useSynchronousApiJobs}
              />
            ) : null}

            {diagnosisRun?.id ? (
              <WorkflowNotice
                tone={
                  deliveryResolution.state === 'report_ready'
                    ? 'success'
                    : deliveryResolution.state === 'failed'
                      ? 'danger'
                      : deliveryResolution.state === 'report_generating'
                        ? 'loading'
                        : 'info'
                }
                title={
                  deliveryResolution.state === 'report_ready'
                    ? '전문 진단서가 준비되었습니다'
                    : deliveryResolution.state === 'failed'
                      ? deliveryResolution.diagnosisFailed
                        ? '진단 단계에서 문제가 발생했습니다'
                        : '진단서 생성 단계에서 문제가 발생했습니다'
                      : deliveryResolution.state === 'report_generating'
                        ? '전문 진단서를 생성하고 있습니다'
                        : '진단은 완료되었고, 전문 진단서를 준비하고 있습니다'
                }
                description={
                  deliveryResolution.state === 'report_ready'
                    ? '아래에서 미리보기와 PDF 다운로드를 바로 진행할 수 있습니다.'
                    : deliveryResolution.state === 'failed'
                      ? deliveryResolution.message || '상태를 확인하고 다시 시도해 주세요.'
                      : deliveryResolution.state === 'report_generating'
                        ? '진단 결과를 기반으로 프리미엄 진단서를 자동 생성 중입니다.'
                        : '잠시 후 자동으로 진단서 생성 상태가 갱신됩니다.'
                }
              />
            ) : null}

            {diagnosisRun?.id ? (
              <DiagnosisReportPanel
                diagnosisRunId={diagnosisRun.id}
                reportStatus={diagnosisRun.report_status ?? null}
                reportAsyncJobStatus={diagnosisRun.report_async_job_status ?? null}
                reportArtifactId={diagnosisRun.report_artifact_id ?? null}
                reportErrorMessage={diagnosisRun.report_error_message ?? null}
              />
            ) : null}

            {hasAdvancedDiagnostics ? (
              <SectionCard
                title="데이터 집계 및 정밀 분석 지표"
                description="분석 과정의 기술적 정보 및 근거 데이터 매핑 현황입니다."
                eyebrow="정밀 분석 리포트"
                collapsible
                defaultCollapsed
                className="border-none bg-slate-50/50"
              >
                {diagnosisResult.document_quality ? (
                  <SurfaceCard tone="muted" padding="sm" className="space-y-3 bg-white border-slate-100">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">데이터 신뢰도 분석</p>
                      <StatusBadge status={diagnosisResult.document_quality.needs_review ? 'warning' : 'success'}>
                        {diagnosisResult.document_quality.parse_reliability_band === 'high' ? '높음' : 
                         diagnosisResult.document_quality.parse_reliability_band === 'medium' ? '보통' : '낮음'} 
                        ({diagnosisResult.document_quality.parse_reliability_score}점)
                      </StatusBadge>
                    </div>
                    <p className="text-base font-medium leading-relaxed text-slate-700">{diagnosisResult.document_quality.summary}</p>
                    <div className="grid gap-2 sm:grid-cols-3">
                      <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-2.5 text-xs font-bold text-slate-600">
                        데이터 수집: {diagnosisResult.document_quality.source_mode === 'pdf_analysis' ? 'AI 엔진 분석' : '텍스트 추출'}
                      </div>
                      <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-2.5 text-xs font-bold text-slate-600">
                        추출 기록: {diagnosisResult.document_quality.total_records}건
                      </div>
                      <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-2.5 text-xs font-bold text-slate-600">
                        분석 단어수: {diagnosisResult.document_quality.total_word_count.toLocaleString()}단어
                      </div>
                    </div>
                  </SurfaceCard>
                ) : null}

                {diagnosisResult.requested_llm_provider ||
                diagnosisResult.actual_llm_provider ||
                diagnosisResult.processing_duration_ms !== undefined ? (
                  <SurfaceCard tone="muted" padding="sm" className="space-y-2 bg-white border-slate-100">
                    <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">엔진 가동 정보</p>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-2.5 text-xs font-bold text-slate-600">
                        분석 모드: {diagnosisResult.llm_profile_used === 'premium' ? '하이엔드 정밀 모델' : '표준 분석'}
                      </div>
                      <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-2.5 text-xs font-bold text-slate-600">
                        처리 안정성: {diagnosisResult.fallback_used ? '최적화 모드' : '안정적'}
                      </div>
                    </div>
                  </SurfaceCard>
                ) : null}

                {diagnosisResult.section_analysis?.length ? (
                  <div className="space-y-3 pt-2">
                    <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">항목별 수집 현황</p>
                    <div className="grid gap-2 md:grid-cols-2">
                      {diagnosisResult.section_analysis.map((item) => (
                        <SurfaceCard key={item.key} tone="muted" padding="sm" className="space-y-1.5 bg-white border-slate-100">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-black text-slate-800">{item.label}</p>
                            <StatusBadge status={item.present ? 'success' : 'warning'}>
                              {item.present ? `${item.record_count}개 감지` : '기록 없음'}
                            </StatusBadge>
                          </div>
                          <p className="text-sm font-medium leading-relaxed text-slate-500">{item.note}</p>
                        </SurfaceCard>
                      ))}
                    </div>
                  </div>
                ) : null}

                {diagnosisResult.admission_axes?.length ? (
                  <div className="space-y-2">
                    <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">입학 축별 평가</p>
                    <div className="grid gap-3 md:grid-cols-2">
                      {diagnosisResult.admission_axes.map((axis) => (
                        <SurfaceCard key={axis.key} padding="sm">
                          <div className="mb-2 flex items-center justify-between gap-2">
                            <p className="text-sm font-bold text-slate-800">{axis.label}</p>
                            <div className="flex items-center gap-1.5">
                              <StatusBadge status={axis.severity === 'low' ? 'success' : axis.severity === 'medium' ? 'warning' : 'danger'}>
                                {axis.band === 'safe' ? '안정' : axis.band === 'warning' ? '주의' : '부족'}
                              </StatusBadge>
                              {axis.status === 'processing' ? (
                                <StatusBadge status="active">진행 중</StatusBadge>
                              ) : (
                                <StatusBadge status="neutral">대기 중</StatusBadge>
                              )}
                            </div>
                          </div>
                          <p className="text-base font-medium leading-7 text-slate-600">{axis.rationale}</p>
                          {axis.evidence_hints?.length ? (
                            <ul className="mt-2 space-y-1">
                              {axis.evidence_hints.slice(0, 2).map((hint) => (
                                <li key={hint} className="text-sm font-semibold text-slate-500">
                                  • {hint}
                                </li>
                              ))}
                            </ul>
                          ) : null}
                        </SurfaceCard>
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className="grid gap-6 xl:grid-cols-2">
                  {diagnosisResult.claims?.length ? <ClaimGroundingPanel claims={diagnosisResult.claims} /> : null}
                  <DiagnosisEvidencePanel
                    citations={evidenceCitations}
                    reviewRequired={reviewRequired}
                    policyFlags={diagnosisRun?.policy_flags ?? []}
                    responseTraceId={responseTraceId}
                  />
                </div>
              </SectionCard>
            ) : null}

            <div className="flex flex-wrap items-center justify-center gap-2">
              <SecondaryButton
                onClick={() => {
                  setStep('GOALS');
                  setDiagnosisResult(null);
                  setDiagnosisRun(null);
                  setDiagnosisJob(null);
                  setDiagnosisRunId(null);
                  setDiagnosisError(null);
                  setFlowError(null);
                  resetTimingPhases();
                  setIsUploading(false);
                }}
              >
                목표 다시 설정
              </SecondaryButton>
              <PrimaryButton onClick={() => navigate(`/app/workshop/${projectId}`)}>
                생기부 워크숍 시작하기
                <ArrowRight size={16} />
              </PrimaryButton>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}


