import type {
  ContentPatch,
  FigureContentBlock,
  FormatPatch as ReportFormatPatch,
  ReportContentBlock,
  ReportDocumentState,
  ReportPatch,
  UniFoliReportSectionId,
} from '../types/reportDocument';
import { ROMAN_REPORT_SECTION_ORDER } from '../types/reportDocument';
import { validateFigureBlock as validateFigureBlockStandalone } from '../utils/figureBlockUtils';
import { validateLatexSyntaxBasic } from '../utils/mathBlockUtils';
import { validateSourceCoverage } from './sourceValidation';

export interface FormatValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  autoFixes: string[];
}

export function validateReportPatch(
  patch: ReportPatch,
  documentState: ReportDocumentState,
): FormatValidationResult {
  const result = createValidationResult();
  if (patch.type === 'format') {
    validateFormatPatch(patch, result);
  } else {
    validateContentPatch(patch, documentState, result);
    mergeValidationResult(result, validateSourceCoverage(patch, documentState));
  }
  result.valid = result.errors.length === 0;
  return result;
}

export function validateReportBeforeExport(documentState: ReportDocumentState): FormatValidationResult {
  const result = createValidationResult();
  const metadata = documentState.metadata;

  if (!metadata.title.trim()) {
    result.errors.push('표지 제목이 필요합니다.');
  }

  for (const field of ['studentName', 'studentId', 'schoolName'] as const) {
    if (!metadata[field].trim()) {
      result.warnings.push(`${field} 값이 비어 있습니다. AI가 임의로 채우지 말고 입력 필요 상태로 두어야 합니다.`);
    }
  }

  const requiredStructure = ['motivation', 'research_method', 'result', 'conclusion', 'references'] as const;
  for (const sectionId of requiredStructure) {
    if (!documentState.sections[sectionId]) {
      result.errors.push(`${sectionId} 섹션이 필요합니다.`);
    }
  }

  if (!romanOrderIsStable(documentState.sectionOrder)) {
    result.errors.push('로마숫자 기반 표준 섹션 순서가 깨졌습니다.');
  }

  for (const figure of documentState.figures) {
    mergeValidationResult(result, validateFigureBlockStandalone(figure, documentState.formatProfile));
  }

  for (const mathBlock of documentState.mathBlocks) {
    const mathResult = validateLatexSyntaxBasic(mathBlock.latex);
    result.errors.push(...mathResult.errors);
    result.warnings.push(...mathResult.warnings);
  }

  if (documentState.formatProfile.citation.requireReferencesSection && !documentState.sections.references) {
    result.errors.push('참고문헌 섹션이 필요합니다.');
  }

  const usedSourceIds = new Set<string>();
  Object.values(documentState.sections).forEach((section) => {
    section.sourceIds.forEach((sourceId) => usedSourceIds.add(sourceId));
    section.contentBlocks.forEach((block) => {
      block.sourceIds?.forEach((sourceId) => usedSourceIds.add(sourceId));
    });
  });
  if (usedSourceIds.size > 0 && documentState.sources.length === 0) {
    result.warnings.push('본문에 sourceIds가 있지만 SourceRecord 목록이 비어 있습니다.');
  }

  result.valid = result.errors.length === 0;
  return result;
}

function validateContentPatch(
  patch: ContentPatch,
  documentState: ReportDocumentState,
  result: FormatValidationResult,
) {
  if (patch.requiresApproval !== true) {
    result.errors.push('ContentPatch는 사용자 승인 전 자동 적용할 수 없습니다.');
  }

  if (!documentState.sections[patch.targetSection] && patch.action !== 'create_section') {
    result.errors.push(`대상 섹션 ${patch.targetSection}을 찾을 수 없습니다.`);
  }

  const targetSection = documentState.sections[patch.targetSection];
  const studentTextLength = (targetSection?.studentAuthoredText || '').trim().length;
  if ((patch.action === 'replace' || patch.action === 'rewrite') && studentTextLength >= 180) {
    result.errors.push('학생이 직접 작성한 substantial content는 AI patch가 자동 replace/rewrite할 수 없습니다.');
  }

  if (patch.action === 'create_section' && documentState.formatProfile.freedom.level !== 'flexible') {
    result.warnings.push('현재 보고서 형식에서는 섹션 추가 자유도가 제한되어 있습니다.');
  }

  const needsSource = patch.contentBlocks.some(looksLikeSourceBackedClaim);
  if (needsSource && patch.sourceIds.length === 0) {
    result.warnings.push('사실 주장 또는 자료 기반 내용에는 sourceIds가 필요합니다. 출처 필요 상태로 표시하세요.');
  }

  for (const block of patch.contentBlocks) {
    if (block.type === 'figure') {
      mergeValidationResult(result, validateFigureBlock(block, documentState));
    }
    if (block.type === 'math') {
      const mathResult = validateLatexSyntaxBasic(block.latex);
      result.errors.push(...mathResult.errors);
      result.warnings.push(...mathResult.warnings);
    }
    if (block.type === 'heading' && /^[IVXLCDM]+\.\s/i.test(block.text)) {
      result.warnings.push('로마숫자 섹션 제목은 AI가 직접 관리하지 않고 template engine이 관리해야 합니다.');
    }
  }
}

function validateFormatPatch(patch: ReportFormatPatch, result: FormatValidationResult) {
  const forbiddenBodyKeys = ['content', 'contentBlocks', 'sections', 'body', 'paragraphs'];
  if (forbiddenBodyKeys.some((key) => Object.prototype.hasOwnProperty.call(patch.changes, key))) {
    result.errors.push('FormatPatch는 본문 내용을 수정할 수 없습니다.');
  }

  if (patch.requiresApproval === false && patch.target !== 'toc' && patch.target !== 'citation') {
    result.warnings.push('승인 없는 FormatPatch는 목차/참고문헌 같은 안전한 자동 갱신에만 사용해야 합니다.');
  }
}

function validateFigureBlock(
  block: FigureContentBlock,
  documentState: ReportDocumentState,
): FormatValidationResult {
  return validateFigureBlockStandalone(block, documentState.formatProfile);
}

function looksLikeSourceBackedClaim(block: ReportContentBlock): boolean {
  if (block.type === 'figure' || block.type === 'table') {
    return true;
  }
  if (block.type !== 'paragraph' && block.type !== 'quote') {
    return false;
  }
  const text = block.text.toLowerCase();
  return /\d|연구|논문|조사|자료|통계|according to|study|survey|data/.test(text);
}

function romanOrderIsStable(sectionOrder: UniFoliReportSectionId[]): boolean {
  const positions = ROMAN_REPORT_SECTION_ORDER.map((sectionId) => sectionOrder.indexOf(sectionId)).filter(
    (index) => index >= 0,
  );
  return positions.every((position, index) => index === 0 || position > positions[index - 1]);
}

function createValidationResult(): FormatValidationResult {
  return {
    valid: true,
    errors: [],
    warnings: [],
    autoFixes: [],
  };
}

function mergeValidationResult(target: FormatValidationResult, addition: FormatValidationResult): void {
  target.errors.push(...addition.errors);
  target.warnings.push(...addition.warnings);
  target.autoFixes.push(...addition.autoFixes);
  target.valid = target.errors.length === 0;
}
