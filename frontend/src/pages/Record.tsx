import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { AlertTriangle, ArrowRight, CheckCircle2, Clock3, FileText, FileUp, RefreshCw, ShieldCheck, TimerReset } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import {
  Input,
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
  page_count: number;
  word_count: number;
  parse_started_at: string | null;
  parse_completed_at: string | null;
  created_at: string;
  updated_at: string;
  content_text: string;
  content_markdown: string;
  parse_metadata: {
    chunk_count?: number;
    table_count?: number;
    warnings?: string[];
    masking?: {
      methods?: string[];
      replacement_count?: number;
      pattern_hits?: Record<string, number>;
    };
    page_failures?: Array<{ page_number?: number; message?: string }>;
  };
}

const IN_PROGRESS_STATUSES = new Set<DocumentStatus>(['masking', 'parsing', 'retrying']);
const SUCCESS_STATUSES = new Set<DocumentStatus>(['parsed', 'partial']);

function formatBytes(value: number | null): string {
  if (!value) return '0 B';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatStatusLabel(status: DocumentStatus): string {
  switch (status) {
    case 'uploaded':
      return '업로드 완료';
    case 'masking':
      return '마스킹 진행 중';
    case 'parsing':
      return '파싱 진행 중';
    case 'retrying':
      return '재시도 중';
    case 'parsed':
      return '파싱 완료';
    case 'partial':
      return '일부 완료';
    case 'failed':
      return '실패';
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
  const { user, isGuestSession } = useAuth();

  const [targetMajor, setTargetMajor] = useState('');
  const [document, setDocument] = useState<DocumentStatusResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isStartingParse, setIsStartingParse] = useState(false);
  const lastTerminalStatus = useRef<DocumentStatus | null>(null);

  const isBusy = isUploading || isStartingParse;
  const previewText = useMemo(() => (document?.content_text ? document.content_text.slice(0, 900) : ''), [document?.content_text]);

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
      toast.success('업로드, 마스킹, 파싱이 모두 완료되었습니다.');
    } else if (document.status === 'partial') {
      toast('일부 경고가 있지만 파싱이 완료되었습니다. 상태를 확인해 주세요.', { icon: '!' });
    } else if (document.status === 'failed') {
      toast.error(document.last_error || '파싱에 실패했습니다. 오류를 확인하고 다시 시도해 주세요.');
    }

    lastTerminalStatus.current = document.status;
  }, [document]);

  const startParse = useCallback(async (documentId: string) => {
    setIsStartingParse(true);
    try {
      const started = await api.post<DocumentStatusResponse>(`/api/v1/documents/${documentId}/parse`);
      setDocument(started);
    } catch (error) {
      console.error('Failed to start parsing:', error);
      toast.error('마스킹/파싱 시작에 실패했습니다.');
    } finally {
      setIsStartingParse(false);
    }
  }, []);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file || isBusy) return;

      setIsUploading(true);
      const loadingId = toast.loading('PDF를 업로드하고 문서를 등록하는 중입니다...');

      try {
        const formData = new FormData();
        formData.append('file', file);
        if (targetMajor.trim()) {
          formData.append('target_major', targetMajor.trim());
          formData.append('title', `${targetMajor.trim()} intake`);
        }

        const created = await api.post<DocumentStatusResponse>('/api/v1/documents/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        setDocument(created);
        toast.success('업로드가 완료되었습니다. 파싱을 시작합니다.', { id: loadingId });
        await startParse(created.id);
      } catch (error) {
        console.error('Upload flow failed:', error);
        toast.error('업로드에 실패했습니다. PDF 파일을 확인해 주세요.', { id: loadingId });
      } finally {
        setIsUploading(false);
      }
    },
    [isBusy, startParse, targetMajor],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    disabled: isBusy,
  });

  const canContinue = Boolean(document && SUCCESS_STATUSES.has(document.status));
  const maskingSummary = document?.parse_metadata?.masking;
  const pageFailures = document?.parse_metadata?.page_failures ?? [];
  const warnings = document?.parse_metadata?.warnings ?? [];
  const stepItems = [
    { id: 'upload', label: '업로드', description: '파일 등록', state: getStepState(document, 'upload') },
    { id: 'masking', label: '마스킹', description: '개인정보 보호 처리', state: getStepState(document, 'masking') },
    { id: 'parsing', label: '파싱', description: '텍스트/구조 분석', state: getStepState(document, 'parsing') },
    { id: 'done', label: '진입 준비', description: '워크숍 이동 가능', state: canContinue ? 'done' : document?.status === 'failed' ? 'error' : 'pending' as 'done' | 'active' | 'pending' | 'error' },
  ] as Array<{ id: string; label: string; description: string; state: 'done' | 'active' | 'pending' | 'error' }>;

  return (
    <div className="mx-auto max-w-7xl space-y-6 py-4">
      <PageHeader
        eyebrow="기록 업로드"
        title="학생부 PDF를 안전하게 처리합니다"
        description="문서 업로드 후 개인정보 마스킹과 파싱 상태를 확인하고, 준비가 끝나면 워크숍으로 이어가세요."
        evidence={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={document?.status === 'failed' ? 'danger' : document && SUCCESS_STATUSES.has(document.status) ? 'success' : 'active'}>
              {document ? formatStatusLabel(document.status) : '업로드 대기'}
            </StatusBadge>
            {document ? <StatusBadge status="neutral">시도 {document.parse_attempts}회</StatusBadge> : null}
          </div>
        }
      />

      <StepIndicator items={stepItems} />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <SectionCard title="문서 업로드" description="PDF 1개(최대 50MB) 업로드를 지원합니다." eyebrow="입력">
          <Input
            id="record-target-major"
            label="목표 학과 (선택)"
            value={targetMajor}
            onChange={event => setTargetMajor(event.target.value)}
            placeholder="예: 경영학과, 컴퓨터공학과"
            hint="입력하면 문서 제목 및 워크숍 연계 정보에 반영됩니다."
          />

          <div
            {...getRootProps()}
            className={`cursor-pointer rounded-2xl border-2 border-dashed p-8 text-left transition-all ${
              isDragActive ? 'border-blue-400 bg-blue-50' : 'border-slate-300 bg-slate-50 hover:border-blue-300 hover:bg-white'
            } ${isBusy ? 'cursor-not-allowed opacity-70' : ''}`}
          >
            <input {...getInputProps({ 'aria-label': '학생부 PDF 업로드' })} />
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-100 text-blue-700">
                  <FileUp size={26} />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-900">PDF 업로드</h2>
                  <p className="mt-1 text-sm font-medium leading-6 text-slate-600">여기에 파일을 드래그하거나 클릭해 선택하세요.</p>
                </div>
              </div>
              <StatusBadge status={isBusy ? 'active' : 'neutral'}>{isBusy ? '처리 중' : '단일 PDF'}</StatusBadge>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <SurfaceCard tone="muted" padding="sm">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">파일명</p>
              <p className="mt-2 text-sm font-bold text-slate-700">{document?.original_filename || '-'}</p>
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
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">텍스트 조각</p>
              <p className="mt-2 text-sm font-bold text-slate-700">{document?.parse_metadata?.chunk_count ?? 0}개</p>
            </SurfaceCard>
          </div>

          {document ? (
            <div className="flex flex-wrap gap-2">
              <SecondaryButton onClick={() => startParse(document.id)} disabled={!document.can_retry || isBusy}>
                <TimerReset size={16} />
                파싱 재시도
              </SecondaryButton>
              <PrimaryButton
                onClick={() => navigate(`/app/workshop/${document.project_id}?major=${encodeURIComponent(targetMajor.trim())}`)}
                disabled={!canContinue}
              >
                워크숍으로 이동
                <ArrowRight size={16} />
              </PrimaryButton>
            </div>
          ) : null}
        </SectionCard>

        <div className="space-y-6">
          <SectionCard title="마스킹 요약" description="개인정보 보호 처리 결과를 확인합니다." eyebrow="보안">
            <div className="flex items-start gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4">
              <ShieldCheck size={18} className="mt-0.5 text-blue-700" />
              <p className="text-sm font-medium leading-6 text-blue-900">
                모든 텍스트는 파싱 전에 마스킹 규칙이 적용됩니다. 처리 방식과 패턴 매칭 결과를 아래에서 확인할 수 있습니다.
              </p>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <SurfaceCard tone="muted" padding="sm">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">적용 방식</p>
                <p className="mt-2 text-sm font-bold text-slate-700">{maskingSummary?.methods?.join(', ') || '대기 중'}</p>
              </SurfaceCard>
              <SurfaceCard tone="muted" padding="sm">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">치환 건수</p>
                <p className="mt-2 text-sm font-bold text-slate-700">{maskingSummary?.replacement_count ?? 0}건</p>
              </SurfaceCard>
              <SurfaceCard tone="muted" padding="sm">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">표 보존</p>
                <p className="mt-2 text-sm font-bold text-slate-700">{document?.parse_metadata?.table_count ?? 0}개</p>
              </SurfaceCard>
            </div>
          </SectionCard>

          <SectionCard title="파싱 미리보기" description="마스킹 처리 후 텍스트 일부를 확인합니다." eyebrow="미리보기">
            <SurfaceCard padding="sm" className="bg-slate-950 text-slate-100">
              <pre className="whitespace-pre-wrap break-words font-mono text-xs leading-6">
                {previewText || '아직 표시할 파싱 텍스트가 없습니다.'}
              </pre>
            </SurfaceCard>
          </SectionCard>

          {warnings.length || pageFailures.length || document?.last_error ? (
            <SectionCard title="경고 및 오류" description="복구가 필요한 페이지 또는 파싱 경고를 확인합니다." eyebrow="확인 필요">
              {document?.last_error ? <WorkflowNotice tone="danger" title="오류 메시지" description={document.last_error} /> : null}
              {warnings.map(warning => (
                <WorkflowNotice key={warning} tone="warning" title="파싱 경고" description={warning} />
              ))}
              {pageFailures.map((failure, index) => (
                <WorkflowNotice
                  key={`${failure.page_number ?? 'na'}-${index}`}
                  tone="warning"
                  title={`${failure.page_number ?? '?'} 페이지 오류`}
                  description={failure.message || '상세 원인을 확인해 주세요.'}
                />
              ))}
            </SectionCard>
          ) : (
            <WorkflowNotice tone="success" title="현재 경고/오류가 없습니다." />
          )}
        </div>
      </div>
    </div>
  );
}
