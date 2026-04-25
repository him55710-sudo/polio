import type {
  ContentPatch,
  ReportContentBlock,
  ReportDocumentState,
  ReportPatch,
  UniFoliReportSectionId,
} from '../types/reportDocument';
import type { FormatValidationResult } from './reportValidation';

export interface SourceNeededClaim {
  blockIndex: number;
  text: string;
  reason: string;
  confidence: 'low' | 'medium' | 'high';
}

const FACTUAL_SECTIONS = new Set<UniFoliReportSectionId>([
  'background_theory',
  'prior_research',
  'data_analysis',
  'result',
  'research_method',
]);

const PERSONAL_OR_REFLECTIVE_SECTIONS = new Set<UniFoliReportSectionId>([
  'motivation',
  'conclusion',
  'student_record_connection',
  'future_research',
  'limitation',
]);

const SOURCE_NEEDED_PATTERNS: Array<{ pattern: RegExp; reason: string }> = [
  { pattern: /연구에 따르면|조사에 따르면|데이터에 따르면/, reason: '연구, 조사, 데이터 근거를 언급했습니다.' },
  { pattern: /일반적으로|로 알려져 있다|알려져 있다/, reason: '일반화된 사실 설명입니다.' },
  { pattern: /선행연구|논문|보고서|통계/, reason: '외부 자료나 선행연구를 언급했습니다.' },
  { pattern: /증가하였다|감소하였다|영향을 미친다|효과가 있다|원인이다/, reason: '변화, 효과, 원인 관계를 주장했습니다.' },
  { pattern: /according to|study|survey|data|research/i, reason: '영문 근거 표현이 포함되어 있습니다.' },
];

export function detectSourceNeededClaims(contentBlocks: ReportContentBlock[]): SourceNeededClaim[] {
  const claims: SourceNeededClaim[] = [];
  contentBlocks.forEach((block, blockIndex) => {
    const text = blockToText(block);
    if (!text.trim()) return;

    if (block.type === 'figure' || block.type === 'table') {
      claims.push({
        blockIndex,
        text: truncate(text, 160),
        reason: block.type === 'figure' ? '그림은 캡션과 출처가 필요합니다.' : '표는 자료 출처가 필요할 수 있습니다.',
        confidence: 'high',
      });
      return;
    }

    for (const { pattern, reason } of SOURCE_NEEDED_PATTERNS) {
      if (pattern.test(text)) {
        claims.push({ blockIndex, text: truncate(text, 160), reason, confidence: 'medium' });
        return;
      }
    }
  });
  return claims;
}

export function hasSourceIdsForFactualPatch(patch: ReportPatch): boolean {
  if (patch.type !== 'content') return true;
  const blockSourceIds = patch.contentBlocks.flatMap((block) => block.sourceIds || []);
  return patch.sourceIds.length > 0 || blockSourceIds.length > 0;
}

export function validateSourceCoverage(
  patch: ReportPatch,
  documentState: ReportDocumentState,
): FormatValidationResult {
  const result: FormatValidationResult = { valid: true, errors: [], warnings: [], autoFixes: [] };
  if (patch.type !== 'content') return result;

  const claims = detectSourceNeededClaims(patch.contentBlocks);
  const isFactualSection = FACTUAL_SECTIONS.has(patch.targetSection);
  const isPersonalSection = PERSONAL_OR_REFLECTIVE_SECTIONS.has(patch.targetSection);
  const hasSources = hasSourceIdsForFactualPatch(patch);

  if ((claims.length > 0 || isFactualSection) && !hasSources && !isPersonalSection) {
    result.warnings.push('출처가 필요한 설명으로 보입니다. sourceIds를 연결하거나 “출처 필요” 상태로 표시하세요.');
  }

  const knownSourceIds = new Set(documentState.sources.map((source) => source.id));
  const missingSourceIds = patch.sourceIds.filter((sourceId) => !knownSourceIds.has(sourceId));
  if (missingSourceIds.length > 0) {
    result.warnings.push(`문서 상태에 없는 출처 ${missingSourceIds.length}개가 patch에 연결되어 있습니다.`);
  }

  if (claims.length > 0) {
    result.autoFixes.push(`${claims.length}개 주장에 출처 점검 표시를 붙일 수 있습니다.`);
  }

  result.valid = result.errors.length === 0;
  return result;
}

function blockToText(block: ReportContentBlock): string {
  switch (block.type) {
    case 'paragraph':
    case 'quote':
    case 'heading':
      return block.text;
    case 'list':
      return block.items.join(' ');
    case 'table':
      return [block.caption, block.headers.join(' '), ...block.rows.map((row) => row.join(' '))].filter(Boolean).join(' ');
    case 'math':
      return [block.latex, block.caption].filter(Boolean).join(' ');
    case 'figure':
      return [block.caption, block.altText].filter(Boolean).join(' ');
    default:
      return '';
  }
}

function truncate(value: string, length: number): string {
  return value.length > length ? `${value.slice(0, length - 1)}…` : value;
}
