import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Download, FileText, Loader2, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

import { api } from '../lib/api';
import type {
  ConsultantDiagnosisArtifactResponse,
  DiagnosisReportMode,
} from '../lib/diagnosis';
import {
  PrimaryButton,
  SecondaryButton,
  SectionCard,
  StatusBadge,
  SurfaceCard,
  WorkflowNotice,
} from './primitives';

interface DiagnosisReportPanelProps {
  diagnosisRunId: string;
  reportStatus?: string | null;
  reportAsyncJobStatus?: string | null;
  reportArtifactId?: string | null;
  reportErrorMessage?: string | null;
}

const MODE_OPTIONS: Array<{
  value: DiagnosisReportMode;
  label: string;
  description: string;
}> = [
  {
    value: 'premium_10p',
    label: '프리미엄 정밀 진단서 (10P)',
    description: '컨설턴트 등급의 레이아웃으로 상세 근거와 입시 분석을 포함한 종합 진단서입니다.',
  },
  {
    value: 'compact',
    label: '컴팩트 요약 보고서',
    description: '핵심 내용만 빠르게 확인할 수 있는 요약형 보고서입니다.',
  },
];

const REPORT_IN_PROGRESS_STATUS = new Set(['AUTO_STARTING', 'QUEUED', 'RUNNING', 'RETRYING', 'SUCCEEDED']);
const REPORT_SYNC_RECOVERY_TRIGGER = 3;
const REPORT_SYNC_MAX_RETRIES = 24;
const PREMIUM_SECTION_ARCHITECTURE: Array<{ id: string; label: string }> = [
  { id: 'executive_summary', label: '종합 진단 요약' },
  { id: 'record_baseline_dashboard', label: '학생부 역량 대시보드' },
  { id: 'narrative_timeline', label: '핵심 활동 타임라인' },
  { id: 'evidence_cards', label: '역량별 근거 데이터' },
  { id: 'strength_analysis', label: '주요 강점 분석' },
  { id: 'risk_analysis', label: '보완점 및 리스크' },
  { id: 'major_fit', label: '전공 적합성 상세 분석' },
  { id: 'interview_questions', label: '예상 면접 질문 선별' },
  { id: 'roadmap', label: '향후 활동 로드맵' },
];
const SECTION_LABEL_BY_ID = PREMIUM_SECTION_ARCHITECTURE.reduce<Record<string, string>>(
  (acc, item) => ({ ...acc, [item.id]: item.label }),
  {},
);

function parseFilename(contentDisposition: string | undefined, fallback: string): string {
  if (!contentDisposition) return fallback;
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return fallback;
    }
  }
  const simpleMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  if (!simpleMatch?.[1]) return fallback;
  return simpleMatch[1];
}

function normalizeStatus(value: string | null | undefined): string | null {
  const normalized = (value || '').trim();
  if (!normalized) return null;
  return normalized.toUpperCase();
}

function resolveBadgeStatus(status: string | null): 'success' | 'warning' | 'danger' | 'neutral' {
  if (status === 'READY') return 'success';
  if (status === 'FAILED') return 'danger';
  if (status && REPORT_IN_PROGRESS_STATUS.has(status)) return 'warning';
  return 'neutral';
}

function resolveBadgeLabel(status: string | null): string {
  if (status === 'READY') return '준비 완료';
  if (status === 'FAILED') return '생성 실패';
  if (status === 'AUTO_STARTING') return '생성 준비 중';
  if (status && REPORT_IN_PROGRESS_STATUS.has(status)) return '분석 진행 중';
  return '미생성';
}

function humanizeSectionId(value: string): string {
  return value
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function DiagnosisReportPanel({
  diagnosisRunId,
  reportStatus,
  reportAsyncJobStatus,
  reportArtifactId,
  reportErrorMessage,
}: DiagnosisReportPanelProps) {
  const [mode, setMode] = useState<DiagnosisReportMode>('premium_10p');
  const [includeAppendix, setIncludeAppendix] = useState(true);
  const [includeCitations, setIncludeCitations] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isRecovering, setIsRecovering] = useState(false);
  const [artifact, setArtifact] = useState<ConsultantDiagnosisArtifactResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reportSyncRetries, setReportSyncRetries] = useState(0);
  const [recoveryTriggered, setRecoveryTriggered] = useState(false);

  const selectedMode = useMemo(() => MODE_OPTIONS.find((item) => item.value === mode) ?? MODE_OPTIONS[0], [mode]);
  const executionMeta = (artifact?.execution_metadata ?? null) as Record<string, unknown> | null;
  const payload = artifact?.payload ?? null;
  const presentSectionIds = useMemo(
    () => new Set((payload?.sections ?? []).map((section) => section.id)),
    [payload],
  );
  const designContract = useMemo(() => {
    if (!payload) return null;
    const renderHints =
      payload.render_hints && typeof payload.render_hints === 'object'
        ? (payload.render_hints as Record<string, unknown>)
        : null;
    if (!renderHints) return null;
    const contractCandidate = renderHints.design_contract;
    if (!contractCandidate || typeof contractCandidate !== 'object') return null;
    return contractCandidate as Record<string, unknown>;
  }, [payload]);
  const contractRequiredOrder = useMemo(() => {
    const hierarchy =
      designContract?.section_hierarchy && typeof designContract.section_hierarchy === 'object'
        ? (designContract.section_hierarchy as Record<string, unknown>)
        : null;
    const requiredOrder = hierarchy?.required_order;
    if (!Array.isArray(requiredOrder)) return [];
    return requiredOrder.map((item) => String(item)).filter(Boolean);
  }, [designContract]);
  const architectureChecklist = useMemo(() => {
    const orderedSectionIds =
      mode === 'premium_10p'
        ? contractRequiredOrder.length
          ? contractRequiredOrder
          : PREMIUM_SECTION_ARCHITECTURE.map((item) => item.id)
        : contractRequiredOrder.length
          ? contractRequiredOrder
          : (payload?.sections ?? []).map((section) => section.id);

    return orderedSectionIds.map((id) => ({
      id,
      label: SECTION_LABEL_BY_ID[id] || humanizeSectionId(id),
      included: presentSectionIds.has(id),
    }));
  }, [contractRequiredOrder, mode, payload, presentSectionIds]);

  const runLifecycleEnabled = mode === 'premium_10p';
  const normalizedRunReportStatus = runLifecycleEnabled
    ? normalizeStatus(reportStatus) ?? normalizeStatus(reportAsyncJobStatus)
    : null;
  const normalizedArtifactStatus = normalizeStatus(artifact?.status ?? null);

  const effectiveStatus = normalizedArtifactStatus ?? normalizedRunReportStatus;
  const reportStateMessage = reportErrorMessage || errorMessage;
  const isAutoGenerating = Boolean(
    runLifecycleEnabled &&
      !artifact &&
      normalizedRunReportStatus &&
      REPORT_IN_PROGRESS_STATUS.has(normalizedRunReportStatus),
  );
  const isRunMarkedReady = Boolean(runLifecycleEnabled && !artifact && normalizedRunReportStatus === 'READY');
  const shouldPollReport = Boolean(
    runLifecycleEnabled &&
      reportSyncRetries < REPORT_SYNC_MAX_RETRIES &&
      (isAutoGenerating || (!artifact && normalizedRunReportStatus === 'READY')),
  );
  const canDownloadReport = Boolean(
    (artifact && artifact.status === 'READY')
      || (normalizedRunReportStatus === 'READY' && reportArtifactId),
  );

  const recoverMissingArtifact = useCallback(async () => {
    if (!runLifecycleEnabled || normalizedRunReportStatus !== 'READY' || artifact) return;
    setIsRecovering(true);
    try {
      const recovered = await api.post<ConsultantDiagnosisArtifactResponse>(
        `/api/v1/diagnosis/${diagnosisRunId}/report`,
        {
          report_mode: mode,
          include_appendix: includeAppendix,
          include_citations: includeCitations,
          force_regenerate: false,
        },
      );
      setArtifact(recovered);
      setIncludeAppendix(recovered.include_appendix);
      setIncludeCitations(recovered.include_citations);
      setReportSyncRetries(0);
      setErrorMessage(recovered.status === 'FAILED' ? recovered.error_message || 'Report generation failed.' : null);
      if (recovered.status === 'READY') {
        toast.success('보고서 정보를 성공적으로 불러왔습니다.');
      }
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      setErrorMessage(
        typeof detail === 'string' && detail.trim()
          ? detail
          : '보고서 정보 동기화가 지연되고 있습니다. 잠시 후 다시 재생성을 시도해 주세요.',
      );
    } finally {
      setIsRecovering(false);
    }
  }, [
    artifact,
    diagnosisRunId,
    includeAppendix,
    includeCitations,
    mode,
    normalizedRunReportStatus,
    runLifecycleEnabled,
  ]);

  const loadExistingArtifact = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const params: Record<string, string | number> = {
        report_mode: mode,
        _ts: Date.now(),
      };
      if (normalizedRunReportStatus === 'READY' && reportArtifactId) {
        params.artifact_id = reportArtifactId;
      }
      const existing = await api.get<ConsultantDiagnosisArtifactResponse>(
        `/api/v1/diagnosis/${diagnosisRunId}/report`,
        { params },
      );
      setArtifact(existing);
      setReportSyncRetries(0);
      setRecoveryTriggered(false);
      setIncludeAppendix(existing.include_appendix);
      setIncludeCitations(existing.include_citations);
      if (existing.status === 'FAILED') {
        setErrorMessage(existing.error_message || '보고서 생성 중 오류가 발생했습니다. 재생성을 시도해 주세요.');
      }
    } catch (error: any) {
      if (error?.response?.status === 404) {
        setArtifact(null);
        if (normalizedRunReportStatus === 'READY') {
          setReportSyncRetries((previous) => previous + 1);
          setErrorMessage('진단은 완료되었고, 전문 진단서를 준비하고 있습니다. 동기화가 길어지면 재생성을 눌러주세요.');
        } else {
          setReportSyncRetries(0);
          setErrorMessage(null);
        }
      } else {
        setErrorMessage('보고서 정보를 불러오는 데 실패했습니다.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [diagnosisRunId, mode, normalizedRunReportStatus, reportArtifactId]);

  useEffect(() => {
    void loadExistingArtifact();
  }, [loadExistingArtifact]);

  useEffect(() => {
    setReportSyncRetries(0);
    setRecoveryTriggered(false);
  }, [diagnosisRunId, mode, reportArtifactId]);

  useEffect(() => {
    if (!runLifecycleEnabled || artifact) return;
    if (normalizedRunReportStatus !== 'READY') return;
    if (reportSyncRetries < REPORT_SYNC_RECOVERY_TRIGGER) return;
    if (recoveryTriggered) return;
    setRecoveryTriggered(true);
    void recoverMissingArtifact();
  }, [
    artifact,
    normalizedRunReportStatus,
    recoverMissingArtifact,
    recoveryTriggered,
    reportSyncRetries,
    runLifecycleEnabled,
  ]);

  useEffect(() => {
    if (!shouldPollReport) return undefined;
    const timer = window.setInterval(() => {
      void loadExistingArtifact();
    }, 2500);
    return () => window.clearInterval(timer);
  }, [loadExistingArtifact, shouldPollReport]);

  const generateReport = useCallback(
    async (forceRegenerate: boolean) => {
      setIsGenerating(true);
      setErrorMessage(null);
      try {
        const created = await api.post<ConsultantDiagnosisArtifactResponse>(
          `/api/v1/diagnosis/${diagnosisRunId}/report`,
          {
            report_mode: mode,
            include_appendix: includeAppendix,
            include_citations: includeCitations,
            force_regenerate: forceRegenerate,
          },
        );
        setArtifact(created);
        if (created.status === 'FAILED') {
          setErrorMessage(created.error_message || '보고서 생성에 실패했습니다.');
          toast.error('보고서 생성 실패');
          return;
        }
        toast.success('전문 진단서 생성이 완료되었습니다.');
      } catch (error: any) {
        const detail = error?.response?.data?.detail;
        const message =
          typeof detail === 'string' && detail.trim()
            ? detail
            : '보고서 생성 중 예기치 않은 오류가 발생했습니다.';
        setErrorMessage(message);
        toast.error(message);
      } finally {
        setIsGenerating(false);
      }
    },
    [diagnosisRunId, includeAppendix, includeCitations, mode],
  );

  const downloadReport = useCallback(async () => {
    setIsDownloading(true);
    try {
      const response = await api.download(`/api/v1/diagnosis/${diagnosisRunId}/report.pdf`, {
        params: {
          artifact_id: artifact?.id ?? reportArtifactId ?? undefined,
          report_mode: mode,
          include_appendix: includeAppendix,
          include_citations: includeCitations,
          force_regenerate: false,
        },
      });
      const filename = parseFilename(
        response.contentDisposition,
        '사용자님의 생기부 진단 보고서.pdf',
      );

      const url = URL.createObjectURL(response.blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success('PDF 다운로드를 시작합니다.');
    } catch {
      toast.error('PDF 다운로드에 실패했습니다.');
    } finally {
      setIsDownloading(false);
    }
  }, [artifact?.id, diagnosisRunId, includeAppendix, includeCitations, mode, reportArtifactId]);

  return (
    <SectionCard
      title="컨설턴트 진단 보고서"
      eyebrow="프리미엄 진단"
      description="진단 완료 후 자동으로 생성됩니다. 수동으로 재생성할 수도 있습니다."
      actions={
        <div className="flex items-center gap-2">
          <StatusBadge status={resolveBadgeStatus(effectiveStatus)}>
            {resolveBadgeLabel(effectiveStatus)}
          </StatusBadge>
        </div>
      }
    >
      <div className="space-y-4">
        {isAutoGenerating ? (
          <WorkflowNotice
            tone="loading"
            title="보고서 자동 생성 중"
            description="진단이 완료되었고, 전문 진단서를 준비하고 있습니다."
          />
        ) : null}

        {isRunMarkedReady ? (
          <WorkflowNotice
            tone="loading"
            title="보고서 생성 완료, 동기화 중"
            description="진단 보고서 생성은 완료되었습니다. 미리보기와 다운로드 정보를 불러오는 중입니다."
          />
        ) : null}

        {!artifact && normalizedRunReportStatus === 'READY' && reportSyncRetries >= REPORT_SYNC_RECOVERY_TRIGGER ? (
          <WorkflowNotice
            tone="warning"
            title="보고서 동기화 지연"
            description={
              isRecovering
                ? '자동 복구를 시도하고 있습니다. 잠시만 기다려주세요.'
                : '동기화가 지연되고 있습니다. 재생성 버튼으로 즉시 복구할 수 있습니다.'
            }
          />
        ) : null}

        {!artifact && normalizedRunReportStatus === 'FAILED' ? (
          <WorkflowNotice
            tone="danger"
            title="보고서 자동 생성 실패"
            description={reportStateMessage || '버튼을 눌러 수동으로 재생성할 수 있습니다.'}
          />
        ) : null}

        {reportStateMessage && !isAutoGenerating && (artifact?.status === 'FAILED' || normalizedRunReportStatus === 'FAILED') ? (
          <WorkflowNotice tone="danger" title="보고서 상태" description={reportStateMessage} />
        ) : (
          <WorkflowNotice
            tone="info"
            title={`선택된 모드: ${selectedMode.label}`}
            description={selectedMode.description}
          />
        )}

        <div className="flex flex-wrap items-center gap-2">
          {canDownloadReport ? (
            <PrimaryButton onClick={downloadReport} disabled={isDownloading}>
              {isDownloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
              PDF 다운로드
            </PrimaryButton>
          ) : (
            <PrimaryButton onClick={() => generateReport(false)} disabled={isGenerating || isLoading}>
              {isGenerating ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
              보고서 생성
            </PrimaryButton>
          )}
          <SecondaryButton onClick={() => generateReport(true)} disabled={isGenerating || isLoading || isRecovering}>
            <RefreshCw size={14} />
            {isRecovering ? '복구 중...' : '재생성'}
          </SecondaryButton>
        </div>

        <SurfaceCard tone="muted" padding="sm">
          <details>
            <summary className="cursor-pointer list-none text-sm font-bold text-slate-800">
              보고서 상세 설정
            </summary>
            <p className="mt-1 text-xs font-medium text-slate-500">
              보고서 모드와 상세 옵션(부록, 주석)을 필요한 경우 변경할 수 있습니다.
            </p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {MODE_OPTIONS.map((option) => (
                <button
                  type="button"
                  key={option.value}
                  onClick={() => setMode(option.value)}
                  className={`rounded-xl border px-3 py-3 text-left transition-colors ${
                    mode === option.value
                      ? 'border-blue-400 bg-blue-50'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <p className="text-sm font-bold text-slate-800">{option.label}</p>
                  <p className="mt-1 text-xs font-medium leading-5 text-slate-600">{option.description}</p>
                </button>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-4 text-sm font-medium text-slate-700">
              <label className="inline-flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={includeAppendix}
                  onChange={(event) => setIncludeAppendix(event.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-[#004aad]"
                />
                근거 부록(Appendix) 포함
              </label>
              <label className="inline-flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={includeCitations}
                  onChange={(event) => setIncludeCitations(event.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-[#004aad]"
                />
                출처/주석(Citations) 포함
              </label>
            </div>
          </details>
        </SurfaceCard>

        {isLoading ? (
          <div className="flex items-center gap-2 text-sm font-medium text-slate-500">
            <Loader2 size={16} className="animate-spin" />
            보고서 데이터를 불러오는 중...
          </div>
        ) : null}

        {payload ? (
          <SurfaceCard tone="muted" padding="sm" className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-bold text-slate-800">{payload.title}</p>
              <StatusBadge status="neutral">v{artifact.version}</StatusBadge>
            </div>
            <p className="text-sm font-medium leading-6 text-slate-600">{payload.subtitle}</p>
            <div className="grid gap-2 md:grid-cols-3">
              <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600">
                분석 섹션: {payload.sections.length}개
              </div>
              <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600">
                기록 근거: {payload.citations.length}건
              </div>
              <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600">
                정밀 검토 메모: {payload.uncertainty_notes.length}건
              </div>
            </div>

            <div className="grid gap-2 md:grid-cols-2">
              {payload.sections.slice(0, 2).map((section) => (
                <div key={section.id} className="rounded-lg border border-slate-200 bg-white p-3">
                  <p className="text-sm font-bold text-slate-800">{section.title}</p>
                  <p className="mt-1 line-clamp-3 text-xs font-medium leading-5 text-slate-600">
                    {section.body_markdown}
                  </p>
                </div>
              ))}
            </div>
          </SurfaceCard>
        ) : (
          <WorkflowNotice
            tone="info"
            title="리포트 미리보기가 준비되지 않았습니다"
            description="보고서 생성이 완료되면 섹션별 요약과 PDF 다운로드 버튼이 이곳에 나타납니다."
          />
        )}

        {(architectureChecklist.length || executionMeta || designContract) ? (
          <SurfaceCard tone="muted" padding="sm">
            <details>
              <summary className="cursor-pointer list-none text-sm font-bold text-slate-800">
                보고서 생성 상세 정보 (관리용)
              </summary>
              {architectureChecklist.length ? (
                <div className="mt-3 rounded-xl border border-slate-200 bg-white p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    리포트 섹션 구성 현황
                  </p>
                  <div className="mt-2 grid gap-2 md:grid-cols-2">
                    {architectureChecklist.map((section) => (
                      <div
                        key={section.id}
                        className={`rounded-lg border px-3 py-2 ${
                          section.included
                            ? 'border-emerald-200 bg-emerald-50'
                            : 'border-amber-200 bg-amber-50'
                        }`}
                      >
                        <p className="text-xs font-semibold text-slate-700">{section.label}</p>
                        <p className="text-[11px] font-semibold text-slate-500">
                          {section.included ? '포함됨' : '데이터 대기 중'}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="mt-3 grid gap-2 text-xs font-semibold text-slate-600 md:grid-cols-2">
                <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
                  저장소: {artifact?.storage_provider || '알 수 없음'} / {artifact?.storage_key || '없음'}
                </div>
                <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
                  분석 엔진: {String(executionMeta?.actual_llm_provider || '알 수 없음')} / {String(executionMeta?.actual_llm_model || '알 수 없음')}
                </div>
                <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
                  우회 실행: {executionMeta?.fallback_used ? '예' : '아니오'}
                  {executionMeta?.fallback_reason ? ` (${String(executionMeta.fallback_reason)})` : ''}
                </div>
                <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
                  소요 시간: {String(executionMeta?.processing_duration_ms ?? '확인 불가')}ms
                </div>
                <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 md:col-span-2">
                  디자인 계약(ID):{' '}
                  {String(designContract?.contract_id || executionMeta?.design_contract_id || '없음')}
                </div>
              </div>
            </details>
          </SurfaceCard>
        ) : null}
      </div>
    </SectionCard>
  );
}


