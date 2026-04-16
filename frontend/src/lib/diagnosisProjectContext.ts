import type { DiagnosisRunResponse } from '@shared-contracts';
import type { ApiErrorInfo } from './apiError';
import { getDiagnosisFailureMessage, isDiagnosisComplete, isDiagnosisFailed } from './diagnosis';
import { IN_PROGRESS_STATUSES, SUCCESS_STATUSES, type DocumentStatus } from '../types/domain';

export interface DiagnosisProjectDocumentSummary {
  id: string;
  project_id: string;
  status: DocumentStatus;
  updated_at: string;
  latest_async_job_id?: string | null;
  latest_async_job_status?: string | null;
  latest_async_job_error?: string | null;
  last_error?: string | null;
}

export type DiagnosisHydrationStep = 'UPLOAD' | 'ANALYSING' | 'RESULT' | 'FAILED';

export interface DiagnosisHydrationDecision {
  mode:
    | 'upload'
    | 'document_in_progress'
    | 'document_failed'
    | 'start_diagnosis'
    | 'run_in_progress'
    | 'run_failed'
    | 'run_completed';
  step: DiagnosisHydrationStep;
  activeDocumentId: string | null;
  activeDiagnosisRunId: string | null;
  shouldStartDiagnosis: boolean;
  flowError: string | null;
}

function normalizeId(value: string | null | undefined): string | null {
  if (typeof value !== 'string') return null;
  const normalized = value.trim();
  return normalized || null;
}

export function resolvePreferredDiagnosisProjectId(
  queryProjectId: string | null | undefined,
  activeProjectId: string | null | undefined,
): string | null {
  return normalizeId(queryProjectId) || normalizeId(activeProjectId);
}

export function shouldApplyDiagnosisResource(
  resourceId: string | null | undefined,
  activeResourceId: string | null | undefined,
): boolean {
  const normalizedResourceId = normalizeId(resourceId);
  const normalizedActiveId = normalizeId(activeResourceId);
  return Boolean(normalizedResourceId && normalizedActiveId && normalizedResourceId === normalizedActiveId);
}

export function isDiagnosisProjectNotFound(
  failure: Pick<ApiErrorInfo, 'debugCode' | 'status'> | null | undefined,
): boolean {
  return normalizeId(failure?.debugCode) === 'PROJECT_NOT_FOUND';
}

export function selectLatestDiagnosisProjectDocument(
  documents: DiagnosisProjectDocumentSummary[],
): DiagnosisProjectDocumentSummary | null {
  if (!documents.length) return null;
  return [...documents].sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0] ?? null;
}

export function resolveDiagnosisHydrationDecision(params: {
  latestRun: DiagnosisRunResponse | null;
  latestDocument: DiagnosisProjectDocumentSummary | null;
}): DiagnosisHydrationDecision {
  const { latestRun, latestDocument } = params;

  if (latestRun) {
    if (isDiagnosisComplete(latestRun)) {
      return {
        mode: 'run_completed',
        step: 'RESULT',
        activeDocumentId: latestDocument?.id ?? null,
        activeDiagnosisRunId: null,
        shouldStartDiagnosis: false,
        flowError: null,
      };
    }

    if (isDiagnosisFailed(latestRun, null)) {
      return {
        mode: 'run_failed',
        step: 'FAILED',
        activeDocumentId: latestDocument?.id ?? null,
        activeDiagnosisRunId: null,
        shouldStartDiagnosis: false,
        flowError: getDiagnosisFailureMessage(latestRun, null),
      };
    }

    return {
      mode: 'run_in_progress',
      step: 'ANALYSING',
      activeDocumentId: latestDocument?.id ?? null,
      activeDiagnosisRunId: latestRun.id,
      shouldStartDiagnosis: false,
      flowError: null,
    };
  }

  if (latestDocument) {
    if (IN_PROGRESS_STATUSES.has(latestDocument.status)) {
      return {
        mode: 'document_in_progress',
        step: 'ANALYSING',
        activeDocumentId: latestDocument.id,
        activeDiagnosisRunId: null,
        shouldStartDiagnosis: false,
        flowError: null,
      };
    }

    if (latestDocument.status === 'failed') {
      return {
        mode: 'document_failed',
        step: 'FAILED',
        activeDocumentId: latestDocument.id,
        activeDiagnosisRunId: null,
        shouldStartDiagnosis: false,
        flowError:
          latestDocument.latest_async_job_error ||
          latestDocument.last_error ||
          '문서 분석에 실패했습니다. 파일 상태를 확인한 뒤 다시 업로드해 주세요.',
      };
    }

    if (SUCCESS_STATUSES.has(latestDocument.status)) {
      return {
        mode: 'start_diagnosis',
        step: 'ANALYSING',
        activeDocumentId: latestDocument.id,
        activeDiagnosisRunId: null,
        shouldStartDiagnosis: true,
        flowError: null,
      };
    }
  }

  return {
    mode: 'upload',
    step: 'UPLOAD',
    activeDocumentId: null,
    activeDiagnosisRunId: null,
    shouldStartDiagnosis: false,
    flowError: null,
  };
}
