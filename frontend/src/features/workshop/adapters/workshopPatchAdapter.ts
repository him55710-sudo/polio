import {
  applyDraftPatch,
  type WorkshopDraftBlock,
  type WorkshopDraftBlockId,
  type WorkshopDraftPatchProposal,
  type WorkshopStructuredDraftState,
} from '../../../lib/workshopCoauthoring';
import {
  createInitialReportDocumentState,
  type ContentPatch,
  type ReportContentBlock,
  type ReportDocumentState,
  type ReportPatch,
  type UniFoliReportSectionId,
} from '../types/reportDocument';

const SUBSTANTIAL_STUDENT_CONTENT_LENGTH = 180;

export interface ConvertWorkshopPatchOptions {
  structuredDraft?: WorkshopStructuredDraftState | null;
  sourceIds?: string[];
  selectedCandidateIds?: string[];
}

export interface ApplyReportPatchResult {
  next: WorkshopStructuredDraftState;
  applied: boolean;
  blockedReason?: string;
  normalizedPatch?: ReportPatch;
}

export function mapWorkshopBlockToReportSection(blockId: WorkshopDraftBlockId): UniFoliReportSectionId {
  switch (blockId) {
    case 'title':
      return 'cover';
    case 'introduction_background':
      return 'motivation';
    case 'body_section_1':
      return 'background_theory';
    case 'body_section_2':
      return 'data_analysis';
    case 'body_section_3':
      return 'result';
    case 'conclusion_reflection_next_step':
      return 'conclusion';
    default:
      return 'appendix';
  }
}

export function mapReportSectionToWorkshopBlock(sectionId: UniFoliReportSectionId): WorkshopDraftBlockId {
  switch (sectionId) {
    case 'cover':
    case 'research_question':
      return 'title';
    case 'motivation':
    case 'research_purpose':
    case 'background_theory':
    case 'prior_research':
      return sectionId === 'background_theory' || sectionId === 'prior_research'
        ? 'body_section_1'
        : 'introduction_background';
    case 'research_method':
    case 'research_process':
      return 'body_section_1';
    case 'data_analysis':
      return 'body_section_2';
    case 'result':
      return 'body_section_3';
    case 'conclusion':
    case 'limitation':
    case 'future_research':
    case 'student_record_connection':
      return 'conclusion_reflection_next_step';
    default:
      return 'body_section_3';
  }
}

export function convertWorkshopDraftPatchToReportPatch(
  patch: WorkshopDraftPatchProposal,
  options: ConvertWorkshopPatchOptions = {},
): ContentPatch {
  const targetSection = mapWorkshopBlockToReportSection(patch.block_id);
  const sourceIds = normalizeStringArray(options.sourceIds);
  const selectedCandidateIds = normalizeStringArray(options.selectedCandidateIds);
  const targetBlock = findWorkshopDraftBlock(options.structuredDraft, patch.block_id);
  const hasProtectedStudentContent = hasSubstantialStudentContent(targetBlock);
  const requestedAction: ContentPatch['action'] = patch.block_id === 'title' ? 'replace' : 'append';
  const safeAction = hasProtectedStudentContent && requestedAction !== 'append' ? 'append' : requestedAction;
  const protectionNote = hasProtectedStudentContent
    ? 'Student-authored content already exists in this section, so the patch is converted to append-only.'
    : '';

  return {
    type: 'content',
    patchId: createPatchId('content'),
    targetSection,
    action: safeAction,
    contentBlocks: markdownToReportContentBlocks(patch.content_markdown),
    contentMarkdown: patch.content_markdown,
    sourceIds,
    selectedCandidateIds,
    rationale: patch.rationale?.trim() || 'AI coauthoring suggestion generated from the workshop conversation.',
    evidenceBoundaryNote: [patch.evidence_boundary_note?.trim(), protectionNote].filter(Boolean).join(' '),
    requiresApproval: true,
    status: 'pending',
  };
}

export function applyReportPatchToStructuredDraft(
  state: WorkshopStructuredDraftState,
  patch: ReportPatch,
  options: { approved?: boolean; allowOverwriteStudentContent?: boolean } = {},
): ApplyReportPatchResult {
  if (patch.type !== 'content') {
    return { next: state, applied: false, blockedReason: 'format_patch_does_not_change_structured_draft' };
  }

  const normalizedPatch = normalizeReportPatchForStudentProtection(state, patch);
  const blockId = mapReportSectionToWorkshopBlock(normalizedPatch.targetSection);
  const contentMarkdown =
    normalizedPatch.contentMarkdown?.trim() || reportContentBlocksToMarkdown(normalizedPatch.contentBlocks);
  const workshopPatch: WorkshopDraftPatchProposal = {
    mode: state.mode || 'section_drafting',
    block_id: blockId,
    heading: resolveStructuredDraftHeading(state, blockId),
    content_markdown: contentMarkdown,
    rationale: normalizedPatch.rationale,
    evidence_boundary_note: normalizedPatch.evidenceBoundaryNote,
    requires_approval: normalizedPatch.requiresApproval,
  };

  const allowOverwriteStudentContent =
    options.allowOverwriteStudentContent ?? (normalizedPatch.action === 'append' || normalizedPatch.action === 'insert');
  const result = applyDraftPatch(state, workshopPatch, {
    approved: options.approved ?? (normalizedPatch.status === 'accepted' || normalizedPatch.status === 'applied'),
    allowOverwriteStudentContent,
  });

  return {
    ...result,
    normalizedPatch,
  };
}

export function structuredDraftToReportDocumentState(
  state: WorkshopStructuredDraftState,
): ReportDocumentState {
  const documentState = createInitialReportDocumentState();
  for (const block of state.blocks) {
    const sectionId = mapWorkshopBlockToReportSection(block.block_id);
    const existing = documentState.sections[sectionId];
    documentState.sections[sectionId] = {
      ...existing,
      contentBlocks: markdownToReportContentBlocks(block.content_markdown || ''),
      studentAuthoredText: block.attribution === 'student-authored' ? block.content_markdown : existing.studentAuthoredText,
      aiGeneratedText: block.attribution !== 'student-authored' ? block.content_markdown : existing.aiGeneratedText,
    };
  }
  return documentState;
}

export function normalizeReportPatchForStudentProtection(
  state: WorkshopStructuredDraftState,
  patch: ContentPatch,
): ContentPatch {
  const blockId = mapReportSectionToWorkshopBlock(patch.targetSection);
  const target = findWorkshopDraftBlock(state, blockId);
  if (!hasSubstantialStudentContent(target)) {
    return patch;
  }
  if (patch.action !== 'replace' && patch.action !== 'rewrite') {
    return { ...patch, requiresApproval: true };
  }
  return {
    ...patch,
    action: 'append',
    requiresApproval: true,
    evidenceBoundaryNote: [
      patch.evidenceBoundaryNote,
      'Protected student-authored text was detected; this patch may only append unless the student explicitly rewrites it.',
    ]
      .filter(Boolean)
      .join(' '),
  };
}

export function hasSubstantialStudentContent(block?: WorkshopDraftBlock | null): boolean {
  return Boolean(
    block?.attribution === 'student-authored' &&
      (block.content_markdown || '').trim().length >= SUBSTANTIAL_STUDENT_CONTENT_LENGTH,
  );
}

export function markdownToReportContentBlocks(markdown: string): ReportContentBlock[] {
  const normalized = String(markdown || '').replace(/\r\n/g, '\n').trim();
  if (!normalized) {
    return [];
  }

  const blocks: ReportContentBlock[] = [];
  const lines = normalized.split('\n');
  let paragraph: string[] = [];
  let listItems: string[] = [];
  let listOrdered = false;

  const flushParagraph = () => {
    const text = paragraph.join('\n').trim();
    if (text) {
      blocks.push({ type: 'paragraph', text });
    }
    paragraph = [];
  };

  const flushList = () => {
    if (listItems.length) {
      blocks.push({ type: 'list', ordered: listOrdered, items: [...listItems] });
    }
    listItems = [];
    listOrdered = false;
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }

    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      flushParagraph();
      flushList();
      blocks.push({
        type: 'heading',
        level: Math.min(headingMatch[1].length, 4) as 1 | 2 | 3 | 4,
        text: headingMatch[2].trim(),
      });
      continue;
    }

    const blockMathMatch = line.match(/^\$\$(.+)\$\$$/);
    if (blockMathMatch) {
      flushParagraph();
      flushList();
      blocks.push({ type: 'math', latex: blockMathMatch[1].trim(), displayMode: 'block', caption: '' });
      continue;
    }

    const quoteMatch = line.match(/^>\s+(.+)$/);
    if (quoteMatch) {
      flushParagraph();
      flushList();
      blocks.push({ type: 'quote', text: quoteMatch[1].trim() });
      continue;
    }

    const bulletMatch = line.match(/^[-*]\s+(.+)$/);
    const orderedMatch = line.match(/^\d+\.\s+(.+)$/);
    if (bulletMatch || orderedMatch) {
      flushParagraph();
      const ordered = Boolean(orderedMatch);
      if (listItems.length && listOrdered !== ordered) {
        flushList();
      }
      listOrdered = ordered;
      listItems.push((bulletMatch?.[1] || orderedMatch?.[1] || '').trim());
      continue;
    }

    flushList();
    paragraph.push(line);
  }

  flushParagraph();
  flushList();

  return blocks.length ? blocks : [{ type: 'paragraph', text: normalized }];
}

export function reportContentBlocksToMarkdown(blocks: ReportContentBlock[]): string {
  return blocks
    .map((block) => {
      switch (block.type) {
        case 'heading':
          return `${'#'.repeat(block.level)} ${block.text}`;
        case 'list':
          return block.items.map((item, index) => `${block.ordered ? `${index + 1}.` : '-'} ${item}`).join('\n');
        case 'quote':
          return `> ${block.text}`;
        case 'table':
          return [block.caption, [block.headers, ...block.rows].map((row) => row.join(' | ')).join('\n')]
            .filter(Boolean)
            .join('\n');
        case 'math':
          return block.displayMode === 'inline' ? `$${block.latex}$` : `$$${block.latex}$$`;
        case 'figure':
          return `![${block.altText}](${block.imageUrl})\n${block.caption}`;
        case 'paragraph':
        default:
          return block.text;
      }
    })
    .filter(Boolean)
    .join('\n\n');
}

function findWorkshopDraftBlock(
  state: WorkshopStructuredDraftState | null | undefined,
  blockId: WorkshopDraftBlockId,
): WorkshopDraftBlock | null {
  return state?.blocks.find((block) => block.block_id === blockId) ?? null;
}

function resolveStructuredDraftHeading(state: WorkshopStructuredDraftState, blockId: WorkshopDraftBlockId): string {
  return state.blocks.find((block) => block.block_id === blockId)?.heading || blockId;
}

function normalizeStringArray(values: unknown): string[] {
  if (!Array.isArray(values)) {
    return [];
  }
  return values.map((value) => String(value || '').trim()).filter(Boolean);
}

function createPatchId(prefix: string): string {
  const random =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `${prefix}-${random}`;
}
