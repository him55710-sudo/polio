import type { MathContentBlock } from '../types/reportDocument';

export interface BasicLatexValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export function validateLatexSyntaxBasic(latex: string): BasicLatexValidationResult {
  const result: BasicLatexValidationResult = { valid: true, errors: [], warnings: [] };
  const text = latex.trim();

  if (!text) {
    result.errors.push('LaTeX 수식이 비어 있습니다.');
  }

  const brackets = [
    ['{', '}'],
    ['(', ')'],
    ['[', ']'],
  ] as const;
  for (const [open, close] of brackets) {
    if (!isBalanced(text, open, close)) {
      result.errors.push(`${open}${close} 괄호 짝이 맞지 않습니다.`);
    }
  }

  const fracCount = (text.match(/\\frac/g) || []).length;
  const fracWithArgsCount = (text.match(/\\frac\s*\{[^{}]+\}\s*\{[^{}]+\}/g) || []).length;
  if (fracCount > fracWithArgsCount) {
    result.warnings.push('\\frac에는 분자와 분모를 모두 중괄호로 감싸는 것이 안전합니다.');
  }

  if (/\\sqrt(?!\s*\{)/.test(text)) {
    result.warnings.push('\\sqrt는 루트 안의 식을 중괄호로 감싸는 것이 안전합니다.');
  }

  if (/[\^_]$/.test(text)) {
    result.warnings.push('위첨자 또는 아래첨자 뒤에 값이 없습니다.');
  }

  result.valid = result.errors.length === 0;
  return result;
}

export function createMathContentBlock(input: {
  latex: string;
  displayMode?: MathContentBlock['displayMode'];
  caption?: string;
  sourceIds?: string[];
}): MathContentBlock {
  return {
    type: 'math',
    latex: input.latex,
    displayMode: input.displayMode || 'block',
    caption: input.caption || '',
    sourceIds: input.sourceIds,
  };
}

export function mathBlockToMarkdown(block: MathContentBlock): string {
  const wrapped = block.displayMode === 'inline' ? `$${block.latex}$` : `$$\n${block.latex}\n$$`;
  return block.caption ? `${wrapped}\n\n수식: ${block.caption}` : wrapped;
}

export function mathBlockToHtml(block: MathContentBlock): string {
  const escapedLatex = escapeHtml(block.latex);
  const caption = block.caption ? `<figcaption>수식: ${escapeHtml(block.caption)}</figcaption>` : '';
  if (block.displayMode === 'inline') {
    return `<span data-latex="${escapedLatex}">\\(${escapedLatex}\\)</span>`;
  }
  return `<figure data-type="math"><pre><code>${escapedLatex}</code></pre>${caption}</figure>`;
}

function isBalanced(text: string, open: string, close: string): boolean {
  let depth = 0;
  for (const char of text) {
    if (char === open) depth += 1;
    if (char === close) depth -= 1;
    if (depth < 0) return false;
  }
  return depth === 0;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
