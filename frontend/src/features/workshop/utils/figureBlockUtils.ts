import type { FigureContentBlock, ReportFormatProfile } from '../types/reportDocument';
import type { FormatValidationResult } from '../validators/reportValidation';

export function validateFigureBlock(
  block: FigureContentBlock,
  formatProfile?: ReportFormatProfile,
): FormatValidationResult {
  const result: FormatValidationResult = { valid: true, errors: [], warnings: [], autoFixes: [] };
  const requireCaption = formatProfile?.figures.requireCaption ?? true;
  const requireSource = formatProfile?.figures.requireSource ?? true;
  const requireAltText = formatProfile?.figures.requireAltText ?? true;

  if (!block.imageUrl.trim()) {
    result.errors.push('그림 URL이 비어 있습니다.');
  }
  if (requireCaption && !block.caption.trim()) {
    result.errors.push('그림에는 caption(캡션)이 필요합니다.');
  }
  if (requireAltText && !block.altText.trim()) {
    result.errors.push('그림에는 대체 텍스트가 필요합니다.');
  }
  if (requireSource && !block.sourceId.trim()) {
    result.errors.push('그림에는 sourceId가 필요합니다.');
  }

  result.valid = result.errors.length === 0;
  return result;
}

export function createFigureContentBlock(input: {
  imageUrl: string;
  caption?: string;
  sourceId?: string;
  altText?: string;
  sourceIds?: string[];
}): FigureContentBlock {
  return {
    type: 'figure',
    imageUrl: input.imageUrl,
    caption: input.caption || '',
    sourceId: input.sourceId || '',
    altText: input.altText || input.caption || '',
    sourceIds: input.sourceIds || (input.sourceId ? [input.sourceId] : []),
  };
}

export function figureBlockToMarkdown(block: FigureContentBlock): string {
  const image = `![${block.altText || '그림'}](${block.imageUrl})`;
  const caption = block.caption ? `[그림] ${block.caption}` : '[그림] 캡션 필요';
  const source = block.sourceId ? `출처: ${block.sourceId}` : '출처: 출처 필요';
  return `${image}\n\n${caption}\n\n${source}`;
}

export function figureBlockToHtml(block: FigureContentBlock): string {
  const caption = block.caption || '캡션 필요';
  const source = block.sourceId || '출처 필요';
  return [
    '<figure data-type="report-figure">',
    `<img src="${escapeHtml(block.imageUrl)}" alt="${escapeHtml(block.altText || caption)}" />`,
    `<figcaption>[그림] ${escapeHtml(caption)}</figcaption>`,
    `<p class="figure-source">출처: ${escapeHtml(source)}</p>`,
    '</figure>',
  ].join('');
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
