import React, { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { CheckCircle2, FileText, Layers3, Loader2, Presentation, Sparkles } from 'lucide-react';
import toast from 'react-hot-toast';
import { api, resolveApiBaseUrl } from '../lib/api';
import { buildInitialGuidedSelection, resolveTemplateSelection } from '../lib/guidedChoice';
import type {
  DiagnosisGuidedPlanResponse,
  DiagnosisResultPayload,
  FormatRecommendation,
  GuidedDraftOutline,
  PageCountOption,
  RecommendedDirection,
  TemplateCandidate,
  TopicCandidate,
} from '../lib/diagnosis';

interface RenderTemplateInfo extends TemplateCandidate {}

interface RenderJobRead {
  id: string;
  draft_id: string;
  render_format: string;
  template_id: string | null;
  template_label: string | null;
  status: string;
  download_url: string | null;
  result_message: string | null;
}

interface DiagnosisGuidedChoicePanelProps {
  diagnosisRunId: string;
  projectId: string;
  diagnosis: DiagnosisResultPayload;
  useSynchronousApiJobs: boolean;
}

function tone(selected: boolean) {
  return selected
    ? 'border-slate-900 bg-slate-900 text-white shadow-lg'
    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-400';
}

function toAbsoluteDownloadUrl(downloadUrl: string): string {
  if (/^https?:\/\//i.test(downloadUrl)) {
    return downloadUrl;
  }
  const apiBase = resolveApiBaseUrl();
  if (downloadUrl.startsWith('/')) {
    return `${apiBase}${downloadUrl}`;
  }
  return `${apiBase}/${downloadUrl}`;
}

function resolveFileName(contentDisposition: string, fallbackName: string): string {
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }
  const simpleMatch = contentDisposition.match(/filename=\"?([^\";]+)\"?/i);
  if (simpleMatch?.[1]) {
    return simpleMatch[1];
  }
  return fallbackName;
}

export function DiagnosisGuidedChoicePanel({
  diagnosisRunId,
  projectId,
  diagnosis,
  useSynchronousApiJobs,
}: DiagnosisGuidedChoicePanelProps) {
  const directions = diagnosis.recommended_directions ?? [];
  const defaultAction = diagnosis.recommended_default_action ?? null;
  const initialSelection = useMemo(() => buildInitialGuidedSelection(diagnosis), [diagnosis]);
  
  const [selectedDirectionId, setSelectedDirectionId] = useState<string | null>(initialSelection.directionId);
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);
  const [selectedPageCount, setSelectedPageCount] = useState<number | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<'pdf' | 'pptx' | 'hwpx' | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [templateGallery, setTemplateGallery] = useState<RenderTemplateInfo[]>([]);
  const [outline, setOutline] = useState<GuidedDraftOutline | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [lastRenderJob, setLastRenderJob] = useState<RenderJobRead | null>(null);
  const [includeProvenanceAppendix, setIncludeProvenanceAppendix] = useState(false);
  const [hideInternalProvenance, setHideInternalProvenance] = useState(true);

  // 대화형 단계(Step) 컨트롤
  const [currentStep, setCurrentStep] = useState<number>(1);

  const downloadRenderedArtifact = async (downloadUrl: string, formatHint?: string) => {
    const absoluteDownloadUrl = toAbsoluteDownloadUrl(downloadUrl);
    const fallbackName = `diagnosis_export.${formatHint || 'pdf'}`;
    const loadingId = toast.loading('Downloading the export...');
    try {
      const file = await api.download(absoluteDownloadUrl);
      const fileName = resolveFileName(file.contentDisposition, fallbackName);
      const objectUrl = window.URL.createObjectURL(file.blob);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = fileName;
      anchor.rel = 'noreferrer';
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 2000);
      toast.success('다운로드 완료.', { id: loadingId });
    } catch (error) {
      console.error(error);
      toast.error('파일을 다운로드할 수 없습니다.', { id: loadingId });
    }
  };

  const waitForRenderJobResult = async (jobId: string, maxAttempts = 15): Promise<RenderJobRead | null> => {
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const current = await api.get<RenderJobRead>(`/api/v1/render-jobs/${jobId}`);
      if (current.download_url || current.status === 'failed' || current.status === 'succeeded') {
        return current;
      }
      await new Promise((resolve) => window.setTimeout(resolve, 1200));
    }
    return null;
  };

  const selectedDirection = useMemo<RecommendedDirection | null>(
    () => directions.find((item) => item.id === selectedDirectionId) ?? null,
    [directions, selectedDirectionId],
  );
  const topicCandidates = selectedDirection?.topic_candidates ?? [];
  const pageCountOptions = selectedDirection?.page_count_options ?? [];
  const formatRecommendations = selectedDirection?.format_recommendations ?? [];
  const recommendedTemplateIds = useMemo(
    () => new Set((selectedDirection?.template_candidates ?? []).map((item) => item.id)),
    [selectedDirection],
  );
  const recommendedDirection = useMemo(
    () => directions.find((item) => item.id === defaultAction?.direction_id) ?? null,
    [defaultAction?.direction_id, directions],
  );

  useEffect(() => {
    setSelectedDirectionId(initialSelection.directionId);
    setSelectedTopicId(initialSelection.topicId);
    setSelectedPageCount(initialSelection.pageCount);
    setSelectedFormat(initialSelection.format);
    setSelectedTemplateId(initialSelection.templateId);
    setOutline(null);
    setLastRenderJob(null);
    setCurrentStep(1); // 초기 세팅 로딩 시 1단계로 강제 리셋
  }, [initialSelection.directionId, initialSelection.format, initialSelection.pageCount, initialSelection.templateId, initialSelection.topicId]);

  useEffect(() => {
    const useDefaultAction = initialSelection.directionId === selectedDirectionId;
    setSelectedTopicId(
      useDefaultAction
        ? (topicCandidates.find((item) => item.id === initialSelection.topicId)?.id ?? topicCandidates[0]?.id ?? null)
        : (topicCandidates[0]?.id ?? null),
    );
    setSelectedPageCount(
      useDefaultAction
        ? (pageCountOptions.find((item) => item.page_count === initialSelection.pageCount)?.page_count ?? pageCountOptions[0]?.page_count ?? null)
        : (pageCountOptions[0]?.page_count ?? null),
    );
    setSelectedFormat(
      useDefaultAction
        ? ((formatRecommendations.find((item) => item.format === initialSelection.format)?.format) ??
            (formatRecommendations.find((item) => item.recommended) ?? formatRecommendations[0])?.format ??
            null)
        : ((formatRecommendations.find((item) => item.recommended) ?? formatRecommendations[0])?.format ?? null),
    );
    setSelectedTemplateId(useDefaultAction ? initialSelection.templateId : null);
    setOutline(null);
    setLastRenderJob(null);
  }, [formatRecommendations, initialSelection.directionId, initialSelection.format, initialSelection.pageCount, initialSelection.templateId, initialSelection.topicId, pageCountOptions, selectedDirectionId, topicCandidates]);

  useEffect(() => {
    if (!selectedFormat) {
      setTemplateGallery([]);
      setSelectedTemplateId(null);
      return;
    }
    let cancelled = false;
    void api
      .get<RenderTemplateInfo[]>(`/api/v1/render-jobs/templates?render_format=${selectedFormat}`)
      .then((templates) => {
        if (!cancelled) {
          setTemplateGallery(templates);
          setSelectedTemplateId((current) =>
            resolveTemplateSelection(templates, {
              currentTemplateId: current,
              preferredTemplateId: selectedDirectionId === initialSelection.directionId ? initialSelection.templateId : null,
              recommendedTemplateIds,
            }),
          );
        }
      })
      .catch(() => {
        if (!cancelled) {
          setTemplateGallery([]);
          setSelectedTemplateId(null);
          toast.error('The template gallery could not be loaded for this format.');
        }
      });
    return () => {
      cancelled = true;
    };
  }, [initialSelection.directionId, initialSelection.templateId, recommendedTemplateIds, selectedDirectionId, selectedFormat]);

  useEffect(() => {
    if (outline) {
      setOutline(null);
      setLastRenderJob(null);
    }
  }, [hideInternalProvenance, includeProvenanceAppendix, selectedFormat, selectedPageCount, selectedTemplateId, selectedTopicId]);

  const buildPlan = async () => {
    if (!selectedDirection || !selectedTopicId || !selectedPageCount || !selectedFormat || !selectedTemplateId) {
      toast.error('Select a direction, topic, length, format, and template first.');
      return;
    }
    setIsGenerating(true);
    try {
      const response = await api.post<DiagnosisGuidedPlanResponse>(
        `/api/v1/diagnosis/${diagnosisRunId}/guided-plan`,
        {
          direction_id: selectedDirection.id,
          topic_id: selectedTopicId,
          page_count: selectedPageCount,
          export_format: selectedFormat,
          template_id: selectedTemplateId,
          include_provenance_appendix: includeProvenanceAppendix,
          hide_internal_provenance_on_final_export: hideInternalProvenance,
        },
      );
      setOutline(response.outline);
      toast.success('가이드 개요가 생성되었습니다. 아래에서 미리보기를 확인하세요!');
    } catch (error) {
      console.error(error);
      toast.error('가이드 개요를 생성할 수 없습니다.');
    } finally {
      setIsGenerating(false);
    }
  };

  const exportOutline = async () => {
    if (!outline?.draft_id || !selectedFormat || !selectedTemplateId) {
      toast.error('Generate the outline before exporting.');
      return;
    }
    setIsExporting(true);
    try {
      const created = await api.post<RenderJobRead>('/api/v1/render-jobs', {
        project_id: projectId,
        draft_id: outline.draft_id,
        render_format: selectedFormat,
        template_id: selectedTemplateId,
        include_provenance_appendix: includeProvenanceAppendix,
        hide_internal_provenance_on_final_export: hideInternalProvenance,
      });
      let resolved = created;
      if (useSynchronousApiJobs) {
        resolved = await api.post<RenderJobRead>(`/api/v1/render-jobs/${created.id}/process`);
      } else {
        try {
          resolved = await api.post<RenderJobRead>(`/api/v1/render-jobs/${created.id}/process`);
        } catch {
          // Fallback to queue mode when inline processing is unavailable.
        }
        if (!resolved.download_url) {
          const eventual = await waitForRenderJobResult(created.id);
          if (eventual) {
            resolved = eventual;
          }
        }
      }
      setLastRenderJob(resolved);
      if (resolved.download_url) {
        await downloadRenderedArtifact(resolved.download_url, resolved.render_format);
      } else if (resolved.status === 'failed') {
        toast.error(resolved.result_message || '파일 생성에 실패했습니다.');
      } else {
        toast.success('파일 생성이 예약되었습니다.');
      }
    } catch (error) {
      console.error(error);
      toast.error('파일 생성을 시작할 수 없습니다.');
    } finally {
      setIsExporting(false);
    }
  };

  // 단계별 다음으로 버튼 활성화 검증 가이드
  const canGoNext = useMemo(() => {
    if (currentStep === 1) return selectedDirectionId !== null;
    if (currentStep === 2) return selectedTopicId !== null;
    if (currentStep === 3) return selectedPageCount !== null && selectedFormat !== null;
    if (currentStep === 4) return selectedTemplateId !== null;
    return false;
  }, [currentStep, selectedDirectionId, selectedTopicId, selectedPageCount, selectedFormat, selectedTemplateId]);

  const stepLabels = [
    { num: 1, label: '탐구 활동 방향' },
    { num: 2, label: '세부 탐구 주제' },
    { num: 3, label: '보고서 규격 설정' },
    { num: 4, label: '템플릿 & 초안 발급' },
  ];

  return (
    <section data-testid="guided-choice-panel" className="space-y-8 rounded-[40px] border border-slate-100 bg-white p-8 shadow-2xl relative overflow-hidden">
      
      {/* 고화질 장식성 배경 빔 */}
      <div className="absolute top-0 right-0 h-96 w-96 rounded-full bg-gradient-to-br from-indigo-50/40 to-transparent blur-3xl pointer-events-none" />

      {/* 진단 요약 및 위반 방지 헤더 */}
      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr] relative z-10">
        <div className="rounded-[28px] border border-slate-100 bg-slate-50/40 p-6 backdrop-blur-sm">
          <p className="text-[11px] font-black uppercase tracking-[0.18em] text-indigo-500">진단 결과 기반 분석 요약</p>
          <p className="mt-3 text-lg font-black text-slate-900 leading-snug">{diagnosis.diagnosis_summary?.overview ?? diagnosis.headline}</p>
          <p className="mt-3 text-xs font-bold leading-relaxed text-slate-500">
            {diagnosis.diagnosis_summary?.reasoning ?? diagnosis.recommended_focus}
          </p>
        </div>
        <div className="rounded-[28px] border border-slate-100 bg-slate-900 p-6 text-white shadow-xl shadow-slate-950/10">
          <p className="text-[11px] font-black uppercase tracking-[0.18em] text-indigo-300">중요 학생부 기재 위반 방지</p>
          <p className="mt-3 text-xs font-bold leading-relaxed text-slate-300">
            {diagnosis.diagnosis_summary?.authenticity_note ??
              '생활기록부에 이미 증명된 사실만을 근거로 삼아야 합니다. 임의의 학업 성취 조작이나 사실 왜곡은 오작동 및 평가 무효 요인이 될 수 있습니다.'}
          </p>
        </div>
      </div>

      {/* 대화형 가이드 4단계 인디케이터 바 */}
      <div className="relative z-10 border-y border-slate-100 py-6 my-2">
        <div className="max-w-3xl mx-auto flex items-center justify-between relative">
          
          {/* 가로 선 */}
          <div className="absolute left-0 right-0 top-1/2 h-[3px] bg-slate-100 -translate-y-1/2 z-0" />
          <div 
            className="absolute left-0 top-1/2 h-[3px] bg-indigo-600 -translate-y-1/2 z-0 transition-all duration-500" 
            style={{ width: `${((currentStep - 1) / (stepLabels.length - 1)) * 100}%` }}
          />

          {stepLabels.map((step) => {
            const isCompleted = step.num < currentStep;
            const isActive = step.num === currentStep;
            return (
              <div key={step.num} className="flex flex-col items-center relative z-10">
                <button
                  type="button"
                  onClick={() => {
                    // 이미 거쳐온 상위 수준 단계거나 바로 앞 단계까지만 터치 이동 허용
                    if (step.num <= currentStep || (step.num === currentStep + 1 && canGoNext)) {
                      setCurrentStep(step.num);
                    }
                  }}
                  className={`flex h-10 w-10 items-center justify-center rounded-full font-black text-sm transition-all duration-300 border-2 ${
                    isActive
                      ? 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-100 scale-110 ring-4 ring-indigo-50'
                      : isCompleted
                        ? 'bg-emerald-500 border-emerald-500 text-white'
                        : 'bg-white border-slate-200 text-slate-400 hover:border-slate-300'
                  }`}
                >
                  {isCompleted ? '✓' : step.num}
                </button>
                <span className={`mt-2.5 text-[11px] font-black tracking-tight ${
                  isActive ? 'text-indigo-600 font-black' : isCompleted ? 'text-emerald-600' : 'text-slate-400'
                }`}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 단계별 대화 가이드 질문 및 콘텐츠 전환 뷰 */}
      <div className="relative z-10 bg-slate-50/20 rounded-3xl border border-slate-100 p-6 min-h-[360px] flex flex-col justify-between">
        <AnimatePresence mode="wait">
          
          {/* Step 1: 탐구 방향성 선택 */}
          {currentStep === 1 && (
            <motion.div
              key="step-1"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              className="space-y-6 flex-1"
            >
              <div className="space-y-1">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-[10px] font-black text-indigo-600">RESEARCH PATHWAY</span>
                <h4 className="text-xl font-black text-slate-900">어떤 방향으로 탐구를 확장하고 보완하고 싶나요?</h4>
                <p className="text-xs font-bold text-slate-400">학생부 진단 결과를 근거로 산출된 가장 적합한 방향 중 한 가지를 제안합니다.</p>
              </div>

              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {directions.map((direction) => (
                  <button
                    key={direction.id}
                    type="button"
                    onClick={() => {
                      setSelectedDirectionId(direction.id);
                      // 선택 시 자연스럽게 바로 다음단계 유도하기 위해 상태 활성화
                    }}
                    className={`rounded-2xl border p-5 text-left transition-all duration-200 relative overflow-hidden group ${
                      direction.id === selectedDirectionId
                        ? 'border-indigo-600 bg-indigo-50/20 text-slate-900 shadow-xl shadow-indigo-100/30'
                        : 'border-slate-200 bg-white text-slate-700 hover:border-slate-400'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                          direction.id === selectedDirectionId ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-500'
                        }`}>{direction.complexity}</span>
                        <h5 className="mt-2 text-base font-black text-slate-900 group-hover:text-indigo-600 transition-colors">{direction.label}</h5>
                      </div>
                      {direction.id === selectedDirectionId && (
                        <CheckCircle2 size={18} className="text-indigo-600 shrink-0" />
                      )}
                    </div>
                    <p className="mt-3 text-xs font-bold leading-relaxed text-slate-500 opacity-90">{direction.summary}</p>
                    <p className="mt-3 text-[11px] font-bold leading-relaxed text-indigo-500">{direction.why_now}</p>
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Step 2: 세부 탐구 주제 선정 */}
          {currentStep === 2 && (
            <motion.div
              key="step-2"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              className="space-y-6 flex-1"
            >
              <div className="space-y-1">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-[10px] font-black text-indigo-600">SELECT TOPIC</span>
                <h4 className="text-xl font-black text-slate-900">보고서로 작성할 구체적인 탐구 주제를 골라주세요.</h4>
                <p className="text-xs font-bold text-slate-400">선택한 탐구 방향에 맞춰 Gemini AI가 정교하게 제안하는 맞춤형 추천 타이틀셋입니다.</p>
              </div>

              <div className="space-y-3 max-w-4xl">
                {topicCandidates.map((topic) => (
                  <button
                    key={topic.id}
                    type="button"
                    onClick={() => setSelectedTopicId(topic.id)}
                    className={`w-full rounded-2xl border p-4 text-left transition-all duration-200 flex items-start gap-3 justify-between ${
                      topic.id === selectedTopicId
                        ? 'border-indigo-600 bg-indigo-50/20 shadow-md shadow-indigo-100/20'
                        : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                    }`}
                  >
                    <div className="min-w-0">
                      <p className="text-sm sm:text-base font-black text-slate-900">{topic.title}</p>
                      <p className="mt-1.5 text-xs font-semibold leading-relaxed text-slate-500">{topic.summary}</p>
                    </div>
                    {topic.id === selectedTopicId ? (
                      <CheckCircle2 size={18} className="text-indigo-600 shrink-0 mt-0.5" />
                    ) : (
                      <div className="h-5 w-5 rounded-full border border-slate-200 shrink-0 mt-0.5" />
                    )}
                  </button>
                ))}
                {topicCandidates.length === 0 && (
                  <p className="text-xs text-slate-400 italic">탐구 방향이 지정되지 않아 추천 주제가 없습니다. 1단계로 돌아가 방향을 선택해 주세요.</p>
                )}
              </div>
            </motion.div>
          )}

          {/* Step 3: 보고서 규격 설정 (분량 및 포맷) */}
          {currentStep === 3 && (
            <motion.div
              key="step-3"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              className="space-y-6 flex-1"
            >
              <div className="space-y-1">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-[10px] font-black text-indigo-600">FORMAT & SIZE</span>
                <h4 className="text-xl font-black text-slate-900">최종 출력할 탐구보고서의 분량과 파일 형식을 결정해 주세요.</h4>
                <p className="text-xs font-bold text-slate-400">학문 깊이에 따른 권장 분량과 학교 제출 규격에 맞는 최적의 문서 형식을 지정합니다.</p>
              </div>

              <div className="grid gap-8 lg:grid-cols-2">
                {/* 권장 분량 선택 */}
                <div className="space-y-3">
                  <h5 className="text-xs font-black uppercase tracking-[0.14em] text-slate-400 flex items-center gap-1.5">
                    <Layers3 size={14} /> 권장 분량 선택
                  </h5>
                  <div className="grid gap-3 sm:grid-cols-3">
                    {pageCountOptions.map((option) => (
                      <button
                        key={option.id}
                        type="button"
                        onClick={() => setSelectedPageCount(option.page_count)}
                        className={`rounded-2xl border p-4 text-left transition-all duration-200 ${
                          option.page_count === selectedPageCount
                            ? 'border-indigo-600 bg-indigo-50/20 shadow-md shadow-indigo-100/20'
                            : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                        }`}
                      >
                        <p className="text-base font-black text-slate-800">{option.label}</p>
                        <p className="mt-1.5 text-[10px] font-semibold leading-relaxed text-slate-400">{option.rationale}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* 내보내기 형식 선택 */}
                <div className="space-y-3">
                  <h5 className="text-xs font-black uppercase tracking-[0.14em] text-slate-400 flex items-center gap-1.5">
                    <FileText size={14} /> 내보내기 파일 형식
                  </h5>
                  <div className="grid gap-3 sm:grid-cols-3">
                    {formatRecommendations.map((item) => (
                      <button
                        key={item.format}
                        type="button"
                        onClick={() => setSelectedFormat(item.format)}
                        className={`rounded-2xl border p-4 text-left transition-all duration-200 ${
                          item.format === selectedFormat
                            ? 'border-indigo-600 bg-indigo-50/20 shadow-md shadow-indigo-100/20'
                            : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                        }`}
                      >
                        <div className="flex items-center gap-2 text-slate-800">
                          {item.format === 'pptx' ? <Presentation size={15} /> : <FileText size={15} />}
                          <p className="text-sm font-black uppercase">{item.format}</p>
                        </div>
                        <p className="mt-1.5 text-[10px] font-semibold leading-relaxed text-slate-400">{item.rationale}</p>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Step 4: 템플릿 선택 및 개요 생성 */}
          {currentStep === 4 && (
            <motion.div
              key="step-4"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              className="space-y-6 flex-1"
            >
              <div className="space-y-1">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-[10px] font-black text-indigo-600">TEMPLATE GALLERY</span>
                <h4 className="text-xl font-black text-slate-900">보고서의 세련됨을 높여줄 디자인 레이아웃을 입혀주세요.</h4>
                <p className="text-xs font-bold text-slate-400">학업 수월성이 강조될 수 있도록 구성된 고품격 템플릿 테마를 입히는 단계입니다.</p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <h5 className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">디자인 템플릿 갤러리</h5>
                  <div className="flex flex-wrap gap-3 text-xs font-bold text-slate-400 bg-slate-100/60 p-1.5 rounded-xl">
                    <label className="flex items-center gap-1.5 cursor-pointer hover:text-slate-700 px-2">
                      <input
                        type="checkbox"
                        checked={includeProvenanceAppendix}
                        onChange={(event) => setIncludeProvenanceAppendix(event.target.checked)}
                        className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      분석 근거 부록 포함
                    </label>
                    <label className="flex items-center gap-1.5 cursor-pointer hover:text-slate-700 px-2">
                      <input
                        type="checkbox"
                        checked={hideInternalProvenance}
                        onChange={(event) => setHideInternalProvenance(event.target.checked)}
                        className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      내부 참조 ID 숨기기
                    </label>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 max-h-[220px] overflow-y-auto p-1 border border-slate-100 rounded-2xl bg-white">
                  {templateGallery.map((template) => (
                    <button
                      key={template.id}
                      type="button"
                      onClick={() => setSelectedTemplateId(template.id)}
                      className={`rounded-xl border p-3.5 text-left transition-all duration-200 flex flex-col justify-between ${
                        template.id === selectedTemplateId
                          ? 'border-indigo-600 bg-indigo-50/15 shadow-md shadow-indigo-100/10'
                          : 'border-slate-200 bg-white hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2 w-full">
                        <div className="min-w-0">
                          <p className="text-sm font-black text-slate-800 truncate">{template.label}</p>
                          <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-400 mt-0.5">{template.category}</p>
                        </div>
                        {recommendedTemplateIds.has(template.id) && (
                          <span className="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-[9px] font-black text-indigo-600 uppercase border border-indigo-100">
                            AI 추천
                          </span>
                        )}
                      </div>
                      <p className="mt-2 text-xs font-medium text-slate-500 leading-relaxed truncate-3-lines">{template.description}</p>
                    </button>
                  ))}
                  {templateGallery.length === 0 && (
                    <p className="text-xs text-slate-400 italic p-4">이 형식에 적용할 수 있는 템플릿이 없습니다. 이전 단계에서 문서 형식을 지정해 주세요.</p>
                  )}
                </div>
              </div>
            </motion.div>
          )}

        </AnimatePresence>

        {/* 위저드 네비게이션 컨트롤 영역 */}
        <div className="mt-8 pt-6 border-t border-slate-100/60 flex items-center justify-between w-full">
          {currentStep > 1 ? (
            <button
              type="button"
              onClick={() => setCurrentStep((prev) => prev - 1)}
              className="rounded-xl border border-slate-200 bg-white px-5 py-3 text-xs font-bold text-slate-600 hover:bg-slate-50 hover:text-slate-800 transition-all duration-200"
            >
              이전 단계
            </button>
          ) : (
            <div />
          )}

          {currentStep < 4 ? (
            <button
              type="button"
              disabled={!canGoNext}
              onClick={() => {
                if (canGoNext) setCurrentStep((prev) => prev + 1);
              }}
              className={`rounded-xl px-6 py-3 text-xs font-black transition-all duration-200 ${
                canGoNext
                  ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg shadow-indigo-100'
                  : 'bg-slate-100 text-slate-400 cursor-not-allowed'
              }`}
            >
              다음 단계로
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={buildPlan}
                disabled={isGenerating || !canGoNext}
                className="rounded-xl bg-slate-900 px-6 py-3 text-xs font-black text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 shadow-lg shadow-slate-950/10 transition-all duration-200"
              >
                {isGenerating ? (
                  <span className="flex items-center gap-1.5">
                    <Loader2 size={14} className="animate-spin" /> 개요 빌딩 중...
                  </span>
                ) : (
                  '가이드 개요 생성하기'
                )}
              </button>
              {outline && (
                <button
                  type="button"
                  onClick={exportOutline}
                  disabled={isExporting}
                  className="rounded-xl border border-slate-900 bg-white px-6 py-3 text-xs font-black text-slate-900 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200"
                >
                  {isExporting ? '초안 내보내는 중...' : '선택한 템플릿 내보내기'}
                </button>
              )}
            </div>
          )}
        </div>

      </div>

      {/* 가이드 개요 생성 후 생성되는 실시간 아웃라인 미리보기 */}
      {outline && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          data-testid="guided-outline-preview"
          className="rounded-[32px] border border-slate-100 bg-slate-50/50 p-6 relative z-10"
        >
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-slate-100 pb-5 mb-5">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.14em] text-indigo-500">생성된 개요 및 초안 미리보기</p>
              <h4 className="mt-2 text-xl font-black text-slate-900">{outline.title}</h4>
              <p className="mt-1.5 text-xs font-semibold leading-relaxed text-slate-500">{outline.summary}</p>
            </div>
            <div className="rounded-2xl border border-slate-100 bg-white px-4 py-3 shrink-0 text-left sm:text-right shadow-sm">
              <p className="text-[10px] font-black uppercase tracking-[0.14em] text-indigo-500">{outline.export_format}</p>
              <p className="mt-0.5 text-xs font-black text-slate-700">{outline.template_label}</p>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {outline.sections.map((section) => (
              <div key={section.id} className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm hover:shadow-md transition-shadow duration-300">
                <p className="text-sm font-black text-slate-900 flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-indigo-600" />
                  {section.title}
                </p>
                <p className="mt-2 text-xs font-semibold leading-relaxed text-slate-500">{section.purpose}</p>
                <div className="mt-3.5 space-y-1.5 text-xs font-bold text-slate-400 bg-slate-50 p-2.5 rounded-xl border border-slate-100/60">
                  <p className="text-[10px] font-black uppercase tracking-[0.05em] text-indigo-500 mb-1">근거 수집 계획</p>
                  {section.evidence_plan.map((item) => (
                    <p key={item} className="leading-relaxed">- {item}</p>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {lastRenderJob?.download_url && (
            <button
              type="button"
              onClick={() => downloadRenderedArtifact(lastRenderJob.download_url || '', lastRenderJob.render_format)}
              className="mt-6 inline-flex rounded-xl bg-indigo-600 px-5 py-3 text-xs font-black text-white hover:bg-indigo-700 shadow-lg shadow-indigo-100 transition-all duration-200"
            >
              방금 생성된 문서 파일 다운로드
            </button>
          )}
        </motion.div>
      )}

    </section>
  );
}
