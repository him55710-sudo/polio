import type { WorkshopDraftPatchProposal } from '../../../lib/workshopCoauthoring';
import {
  convertWorkshopDraftPatchToReportPatch,
  reportContentBlocksToMarkdown,
} from '../adapters/workshopPatchAdapter';
import type { FormatValidationResult } from '../validators/reportValidation';
import type { ReportPatch, UniFoliReportSectionId } from '../types/reportDocument';

export type ReviewablePatch = ReportPatch | WorkshopDraftPatchProposal;

export const REPORT_SECTION_LABELS: Record<UniFoliReportSectionId, string> = {
  cover: '표지',
  table_of_contents: '목차',
  motivation: 'I. 연구 동기 및 목적',
  research_purpose: '연구 목적',
  research_question: '연구 질문',
  background_theory: 'II. 이론적 배경',
  prior_research: '선행연구',
  research_method: 'III. 연구 방법',
  research_process: '연구 과정',
  data_analysis: '자료 분석',
  result: 'IV. 연구 결과',
  conclusion: 'V. 결론 및 제언',
  limitation: '한계와 보완점',
  future_research: '후속 연구',
  student_record_connection: '학생 기록 연결',
  references: '참고 문헌',
  appendix: '부록',
};

const ACTION_LABELS: Record<string, string> = {
  insert: '선택한 위치에 삽입',
  append: '기존 내용 뒤에 추가',
  replace: '섹션 내용 교체',
  rewrite: '문장 다시 쓰기',
  create_section: '새 섹션 만들기',
  format: '양식 조정',
};

export function isReportPatch(patch: ReviewablePatch): patch is ReportPatch {
  return (patch as ReportPatch).type === 'content' || (patch as ReportPatch).type === 'format';
}

export function normalizePatchForReview(patch: ReviewablePatch): ReportPatch {
  return isReportPatch(patch) ? patch : convertWorkshopDraftPatchToReportPatch(patch);
}

export function formatPatchTargetLabel(patch: ReviewablePatch): string {
  const normalized = normalizePatchForReview(patch);
  if (normalized.type === 'format') {
    return formatPatchFormatTarget(normalized.target);
  }
  return REPORT_SECTION_LABELS[normalized.targetSection] || normalized.targetSection;
}

export function formatPatchActionLabel(patch: ReviewablePatch): string {
  const normalized = normalizePatchForReview(patch);
  if (normalized.type === 'format') return ACTION_LABELS.format;
  return ACTION_LABELS[normalized.action] || normalized.action;
}

export function formatPatchPreview(patch: ReviewablePatch): string {
  const normalized = normalizePatchForReview(patch);
  if (normalized.type === 'content') {
    return normalized.contentMarkdown?.trim() || reportContentBlocksToMarkdown(normalized.contentBlocks);
  }
  return Object.entries(normalized.changes)
    .map(([key, value]) => `${formatPatchFormatTarget(key)}: ${formatValue(value)}`)
    .join('\n');
}

export function getPatchSourceIds(patch: ReviewablePatch): string[] {
  const normalized = normalizePatchForReview(patch);
  return normalized.type === 'content' ? normalized.sourceIds : [];
}

export function summarizeValidation(validation?: FormatValidationResult | null): {
  hasErrors: boolean;
  hasWarnings: boolean;
  messages: string[];
  tone: 'success' | 'warning' | 'danger';
} {
  const errors = validation?.errors || [];
  const warnings = validation?.warnings || [];
  if (errors.length > 0) {
    return { hasErrors: true, hasWarnings: warnings.length > 0, messages: [...errors, ...warnings], tone: 'danger' };
  }
  if (warnings.length > 0) {
    return { hasErrors: false, hasWarnings: true, messages: warnings, tone: 'warning' };
  }
  return {
    hasErrors: false,
    hasWarnings: false,
    messages: ['표준 보고서 양식에 맞는 제안입니다.'],
    tone: 'success',
  };
}

function formatPatchFormatTarget(target: string): string {
  const labels: Record<string, string> = {
    cover: '표지',
    toc: '목차',
    typography: '글꼴과 줄간격',
    numbering: '번호 체계',
    citation: '출처와 참고문헌',
    math: '수식 형식',
    figures: '그림 형식',
    freedom: '보고서 자유도',
  };
  return labels[target] || target;
}

function formatValue(value: unknown): string {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  if (Array.isArray(value)) {
    return `${value.length}개 항목`;
  }
  if (value && typeof value === 'object') {
    return '세부 설정 변경';
  }
  return '변경';
}
