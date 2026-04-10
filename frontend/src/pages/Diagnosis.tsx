import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { useDropzone } from 'react-dropzone';
import { 
  Sparkles, 
  ArrowRight, 
  Zap 
} from 'lucide-react';

import toast from 'react-hot-toast';

import { useAuthStore } from '../store/useAuthStore';
import { useOnboardingStore } from '../store/useOnboardingStore';
import { api } from '../lib/api';
import { getApiErrorMessage } from '../lib/apiError';
import { shouldUseSynchronousApiJobs } from '../lib/config';

import { 
  AsyncJobRead, 
  DiagnosisRunResponse, 
  DiagnosisResultPayload 
} from '../types/api';
import { 
  buildRankedGoals, 
  createInitialTimingPhases, 
  TimingPhaseStatus,
  mergeDiagnosisPayload,
  isDiagnosisComplete,
  isDiagnosisFailed,
  getDiagnosisFailureMessage,
  resolveDiagnosisDeliveryState,
  DIAGNOSIS_STORAGE_KEY
} from '../lib/diagnosis';

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
import { AsyncJobStatusCard } from '../components/AsyncJobStatusCard';
import { useAsyncJob } from '../hooks/useAsyncJob';
import { TERMINAL_STATUSES, SUCCESS_STATUSES } from '../types/domain';

import { DiagnosisGoals } from '../components/diagnosis/DiagnosisGoals';
import { DiagnosisUpload } from '../components/diagnosis/DiagnosisUpload';
import { DiagnosisResultDisplay } from '../components/diagnosis/DiagnosisResultDisplay';
import { DiagnosisGuidedChoicePanel } from '../components/DiagnosisGuidedChoicePanel';
import { DiagnosisReportPanel } from '../components/DiagnosisReportPanel';
import { ProcessTimingDashboard } from '../components/ProcessTimingDashboard';
import { ClaimGroundingPanel } from '../components/ClaimGroundingPanel';
import { DiagnosisEvidencePanel } from '../components/DiagnosisEvidencePanel';


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

const PARSE_SUCCESS_STATUSES = SUCCESS_STATUSES;
const PARSE_TERMINAL_STATUSES = TERMINAL_STATUSES;

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

  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(preselectedProjectId);
  const [isUploading, setIsUploading] = useState(false);
  const [diagnosisResult, setDiagnosisResult] = useState<DiagnosisResultPayload | null>(null);
  const [diagnosisRunId, setDiagnosisRunId] = useState<string | null>(null);
  const [diagnosisRun, setDiagnosisRun] = useState<DiagnosisRunResponse | null>(null);
  const [diagnosisJob, setDiagnosisJob] = useState<AsyncJobRead | null>(null);
  const [diagnosisError, setDiagnosisError] = useState<string | null>(null);
  const [isRetryingDiagnosis, setIsRetryingDiagnosis] = useState(false);
  const [flowError, setFlowError] = useState<string | null>(null);
  const [timingPhases, setTimingPhases] = useState<TimingPhaseMap>(() => ({
    upload: { status: 'idle', startedAt: null, finishedAt: null, note: '데이터 전송 중' },
    parse: { status: 'idle', startedAt: null, finishedAt: null, note: '생활기록부 정보 추출 중' },
    diagnosis: { status: 'idle', startedAt: null, finishedAt: null, note: 'AI 기반 맞춤형 진단 중' },
  }));
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

  // 1. 문서 분석 폴링
  const { data: polledDoc } = useAsyncJob<DiagnosisDocumentStatus>({
    url: activeDocumentId ? `/api/v1/documents/${activeDocumentId}` : null,
    isTerminal: (doc) => PARSE_TERMINAL_STATUSES.has(doc.status),
    enabled: step === 'ANALYSING' && !!activeDocumentId,
    onSuccess: (doc) => {
      triggerInlineParseProcessing(doc);
    },
  });

  useEffect(() => {
    if (!polledDoc || step !== 'ANALYSING') return;
    triggerInlineParseProcessing(polledDoc);

    if (PARSE_TERMINAL_STATUSES.has(polledDoc.status)) {
      if (polledDoc.latest_async_job_id) {
        parseProcessKickoffRef.current.delete(polledDoc.latest_async_job_id);
      }

      if (!PARSE_SUCCESS_STATUSES.has(polledDoc.status)) {
        const parseError = polledDoc.latest_async_job_error || polledDoc.last_error || '문서 분석에 실패했습니다.';
        finishTimingPhase('parse', 'failed', parseError);
        setDiagnosisError(parseError);
        setFlowError(parseError);
        setStep('FAILED');
        setIsUploading(false);
      } else if (!hasDocumentContent(polledDoc)) {
        const emptyError = '진단 가능한 텍스트를 찾지 못했습니다.';
        finishTimingPhase('parse', 'failed', emptyError);
        setDiagnosisError(emptyError);
        setFlowError(emptyError);
        setStep('FAILED');
        setIsUploading(false);
      } else {
        finishTimingPhase('parse', 'done', polledDoc.page_count ? `분석 완료 (${polledDoc.page_count}쪽)` : '분석 완료');
        beginTimingPhase('diagnosis', '진단 생성 진행 중');
        startDiagnosisForProject(polledDoc.project_id);
      }
    }
  }, [polledDoc, step, finishTimingPhase, beginTimingPhase, startDiagnosisForProject]);

  // 2. 진단 실행 폴링
  const { data: polledRun } = useAsyncJob<DiagnosisRunResponse>({
    url: diagnosisRunId ? `/api/v1/diagnosis/${diagnosisRunId}` : null,
    isTerminal: (run) => isDiagnosisComplete(run) || isDiagnosisFailed(run, null),
    enabled: step === 'ANALYSING' && !!diagnosisRunId,
  });

  useEffect(() => {
    if (!polledRun || step !== 'ANALYSING') return;
    void syncDiagnosisRun(polledRun.id);
  }, [polledRun, step, syncDiagnosisRun]);

  // 3. 리포트 생성 폴링
  const { data: polledReportRun } = useAsyncJob<DiagnosisRunResponse>({
    url: step === 'RESULT' && diagnosisRun?.id ? `/api/v1/diagnosis/${diagnosisRun.id}` : null,
    isTerminal: (run) => {
      const status = (run.report_status || run.report_async_job_status || '').toUpperCase();
      return status === 'READY' || status === 'FAILED';
    },
    enabled: step === 'RESULT' && !!diagnosisRun?.id && (diagnosisRun.report_status !== 'READY'),
    intervalMs: 3000,
  });

  useEffect(() => {
    if (polledReportRun) {
      setDiagnosisRun(polledReportRun);
    }
  }, [polledReportRun]);

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
        setActiveDocumentId(uploadRes.id);
        triggerInlineParseProcessing(parseStarted);

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
      description: '워크숍 진입',
      state: step === 'RESULT' ? 'active' : 'pending',
    },
  ];

  const headerTitle = useMemo(() => {
    switch (step) {
      case 'GOALS': return '목표 대학교 진단';
      case 'UPLOAD': return '생활기록부 업로드';
      case 'ANALYSING': return 'AI 정밀 분석 중';
      case 'RESULT': return 'AI 진단 결과';
      case 'FAILED': return '진단 분석 실패';
      default: return '진단 서비스';
    }
  }, [step]);

  const headerDescription = useMemo(() => {
    switch (step) {
      case 'GOALS': return '희망하는 대학교와 학과를 선택해 주세요. 목표에 맞춘 정밀 진단을 시작합니다.';
      case 'UPLOAD': return '분석을 위해 본인의 생활기록부 PDF 파일을 업로드해 주세요.';
      case 'ANALYSING': return '기록된 내용을 바탕으로 대학별 합격 가능성과 강점을 분석하고 있습니다.';
      case 'RESULT': return '분석이 완료되었습니다. 결과 리포트와 추천 워크숍 내용을 확인하세요.';
      case 'FAILED': return '분석 과정에서 문제가 발생했습니다. 내용을 확인하고 다시 시도해 주세요.';
      default: return '사용자 맞춤형 대학 입시 진단 서비스입니다.';
    }
  }, [step]);

  const shouldShowTimingDashboard = step === 'ANALYSING' || (step === 'UPLOAD' && isUploading);
  const timingPhaseItems = Object.entries(timingPhases).map(([key, phase]) => ({
    id: key,
    label: phase.note || '',
    status: phase.status,
    startTime: phase.startedAt,
    endTime: phase.finishedAt,
  }));

  const hasDocumentContent = (doc: DiagnosisDocumentStatus) => Boolean(doc.content_text?.trim());

  return (
    <div className="mx-auto max-w-6xl space-y-8 py-8 animate-in fade-in duration-700">
      <div className="relative overflow-hidden rounded-[2.5rem] bg-gradient-to-br from-[#004aad] to-[#0070f3] p-8 md:p-12 shadow-2xl shadow-blue-500/20">
        <div className="absolute -right-24 -top-24 h-96 w-96 rounded-full bg-white/10 blur-3xl animate-pulse" />
        <div className="absolute -bottom-24 -left-24 h-96 w-96 rounded-full bg-cyan-400/20 blur-3xl" />
        
        <div className="relative z-10 space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-1.5 backdrop-blur-md ring-1 ring-white/20">
            <Sparkles size={14} className="text-cyan-300" />
            <span className="text-sm font-bold tracking-tight text-cyan-50">프리미엄 AI 분석</span>
          </div>
          <h1 className="text-4xl font-black tracking-tight text-white md:text-5xl lg:leading-[1.15]">
            {headerTitle}
          </h1>
          <p className="max-w-2xl text-lg font-medium leading-relaxed text-blue-100/80">
            {headerDescription}
          </p>
        </div>
      </div>

      {shouldShowProgressRail && (
        <div className="px-4">
          <StepIndicator items={stepItems} />
        </div>
      )}

      {shouldShowProgressRail && shouldShowTimingDashboard && (
        <div className="animate-in slide-in-from-top-4 duration-500">
          <ProcessTimingDashboard
            phases={timingPhaseItems}
            title="실시간 진단 현황"
            description="데이터 마스킹과 정밀 분석이 실시간으로 진행 중입니다"
          />
        </div>
      )}

      <AnimatePresence mode="wait">
        {step === 'GOALS' && (
          <DiagnosisGoals
            goalList={goalList}
            isEditingGoals={isEditingGoals}
            setIsEditingGoals={setIsEditingGoals}
            univInput={univInput}
            setUnivInput={setUnivInput}
            currentUniv={currentUniv}
            setCurrentUniv={setCurrentUniv}
            currentMajor={currentMajor}
            setCurrentMajor={setCurrentMajor}
            handleAddGoal={handleAddGoal}
            removeGoal={removeGoal}
            saveGoals={saveGoals}
            onContinue={() => setStep('UPLOAD')}
            cancelEdit={() => {
              setIsEditingGoals(false);
              if (user) {
                const initial = buildRankedGoals(user, 6).map((goal, idx) => ({
                  id: idx === 0 ? 'main' : `interest-${idx - 1}`,
                  university: goal.university,
                  major: goal.major,
                }));
                setGoalList(initial);
              }
            }}
          />
        )}

        {step === 'UPLOAD' && (
          <DiagnosisUpload
            getRootProps={getRootProps}
            getInputProps={getInputProps}
            isDragActive={isDragActive}
            isUploading={isUploading}
            handleOpenFileDialog={handleOpenFileDialog}
            handleDropzoneKeyDown={handleDropzoneKeyDown}
            setStep={setStep}
            flowError={flowError}
          />
        )}

        {step === 'ANALYSING' && (
          <motion.div
            key="analysing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="space-y-6"
          >
            <WorkflowNotice
              tone="loading"
              title="학생부 기록을 꼼꼼하게 분석하고 있습니다"
              description="내용 분석이 끝나면 자동으로 진단 단계로 넘어가며, 페이지를 유지하면 상태가 자동 갱신됩니다"
            />
            <AsyncJobStatusCard
              job={diagnosisJob}
              runStatus={diagnosisRun?.status}
              errorMessage={diagnosisRun?.error_message}
            />
          </motion.div>
        )}

        {step === 'FAILED' && (
          <motion.div
            key="failed"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            <WorkflowNotice
              tone="danger"
              title="진단 실행에 실패했습니다"
              description={flowError || diagnosisError || '작업 상태를 확인하고 다시 시도해 주세요.'}
            />

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
              {diagnosisJob?.status === 'failed' && (
                <PrimaryButton onClick={retryDiagnosis} disabled={isRetryingDiagnosis}>
                  {isRetryingDiagnosis ? '재시도 중...' : '진단 재시도'}
                </PrimaryButton>
              )}
            </div>
          </motion.div>
        )}

        {step === 'RESULT' && diagnosisResult && (
          <motion.div
            key="result-view"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-8"
          >
            <DiagnosisResultDisplay diagnosisResult={diagnosisResult} />

            {diagnosisRun?.id && projectId && (
              <DiagnosisGuidedChoicePanel
                diagnosisRunId={diagnosisRun.id}
                projectId={projectId}
                diagnosis={diagnosisResult}
                useSynchronousApiJobs={useSynchronousApiJobs}
              />
            )}

            {diagnosisRun?.id && (
              <DiagnosisReportPanel
                diagnosisRunId={diagnosisRun.id}
                reportStatus={diagnosisRun.report_status ?? null}
                reportAsyncJobStatus={diagnosisRun.report_async_job_status ?? null}
                reportArtifactId={diagnosisRun.report_artifact_id ?? null}
                reportErrorMessage={diagnosisRun.report_error_message ?? null}
              />
            )}

            {hasAdvancedDiagnostics && (
              <SectionCard
                title="데이터 집계 및 정밀 분석 지표"
                description="분석 과정의 기술적 정보 및 근거 데이터 매핑 현황입니다."
                eyebrow="정밀 분석 리포트"
                collapsible
                defaultCollapsed
                className="border-none bg-slate-50/50"
              >
                <div className="grid gap-6 xl:grid-cols-2">
                  {diagnosisResult.claims?.length ? (
                    <ClaimGroundingPanel claims={diagnosisResult.claims} />
                  ) : null}
                  <DiagnosisEvidencePanel
                    citations={evidenceCitations}
                    reviewRequired={reviewRequired}
                    policyFlags={diagnosisRun?.policy_flags ?? []}
                    responseTraceId={responseTraceId}
                  />
                </div>
              </SectionCard>
            )}

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
                생활기록부 워크숍 시작하기
                <ArrowRight size={16} />
              </PrimaryButton>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}


