import assert from 'node:assert/strict';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import { ChoiceCardGroup } from '../src/features/workshop/components/ChoiceCardGroup';
import { PatchReviewCard } from '../src/features/workshop/components/PatchReviewCard';
import {
  applyReportPatchToStructuredDraft,
  convertWorkshopDraftPatchToReportPatch,
  structuredDraftToReportDocumentState,
} from '../src/features/workshop/adapters/workshopPatchAdapter';
import {
  buildCitationText,
  buildReferencesMarkdown,
  convertPaperResultToSourceRecord,
  dedupeSourceRecords,
  groupSourcesBySection,
  sourceRecordToCitationText,
} from '../src/features/workshop/adapters/sourceAdapter';
import { validateFigureBlock } from '../src/features/workshop/utils/figureBlockUtils';
import { validateLatexSyntaxBasic } from '../src/features/workshop/utils/mathBlockUtils';
import {
  buildResearchQueryFromMessage,
  inferTargetSectionFromResearchMessage,
  isResearchRequestMessage,
} from '../src/features/workshop/utils/researchIntent';
import { validateSourceCoverage } from '../src/features/workshop/validators/sourceValidation';
import {
  createDefaultReportFormatProfile,
  createInitialReportDocumentState,
  type ContentPatch,
  type SourceRecord,
} from '../src/features/workshop/types/reportDocument';
import { validateReportBeforeExport, validateReportPatch } from '../src/features/workshop/validators/reportValidation';
import {
  createEmptyStructuredDraft,
  type WorkshopDraftPatchProposal,
  type WorkshopStructuredDraftState,
} from '../src/lib/workshopCoauthoring';

test('WorkshopDraftPatchProposal converts into a pending ContentPatch', () => {
  const patch = makeWorkshopPatch();
  const reportPatch = convertWorkshopDraftPatchToReportPatch(patch, { sourceIds: ['source-1'] });

  assert.equal(reportPatch.type, 'content');
  assert.equal(reportPatch.targetSection, 'background_theory');
  assert.equal(reportPatch.requiresApproval, true);
  assert.equal(reportPatch.status, 'pending');
  assert.deepEqual(reportPatch.sourceIds, ['source-1']);
  assert.match(reportPatch.contentMarkdown || '', /first draft/i);
});

test('student-authored content is protected from automatic replace', () => {
  const structuredDraft = makeStructuredDraftWithStudentContent();
  const reportPatch = convertWorkshopDraftPatchToReportPatch(
    { ...makeWorkshopPatch(), block_id: 'title' },
    { structuredDraft },
  );

  assert.equal(reportPatch.action, 'append');

  const result = applyReportPatchToStructuredDraft(
    structuredDraft,
    { ...reportPatch, status: 'accepted' },
    { approved: true },
  );
  assert.equal(result.applied, true);
  const titleBlock = result.next.blocks.find((block) => block.block_id === 'title');
  assert.match(titleBlock?.content_markdown || '', /student sentence 1/);
  assert.match(titleBlock?.content_markdown || '', /first draft/);
});

test('a converted patch does not mutate the structured draft before approval', () => {
  const structuredDraft = createEmptyStructuredDraft('section_drafting');
  const before = JSON.stringify(structuredDraft);
  convertWorkshopDraftPatchToReportPatch(makeWorkshopPatch(), { structuredDraft });

  assert.equal(JSON.stringify(structuredDraft), before);
});

test('approval applies ContentPatch to structured draft only through applyReportPatchToStructuredDraft', () => {
  const structuredDraft = createEmptyStructuredDraft('section_drafting');
  const reportPatch = convertWorkshopDraftPatchToReportPatch(makeWorkshopPatch(), { structuredDraft });
  const pendingResult = applyReportPatchToStructuredDraft(structuredDraft, reportPatch, { approved: false });
  assert.equal(pendingResult.applied, true);
  assert.equal(
    pendingResult.next.blocks.find((block) => block.block_id === 'body_section_1')?.attribution,
    'ai-suggested',
  );

  const acceptedResult = applyReportPatchToStructuredDraft(structuredDraft, { ...reportPatch, status: 'accepted' }, { approved: true });
  assert.equal(acceptedResult.applied, true);
  assert.equal(
    acceptedResult.next.blocks.find((block) => block.block_id === 'body_section_1')?.attribution,
    'ai-inserted-after-approval',
  );
});

test('SourceRecord dedupe merges duplicate source usage', () => {
  const sources = dedupeSourceRecords([
    makeSource({ id: 'a', usedInSections: ['background_theory'] }),
    makeSource({ id: 'b', usedInSections: ['result'] }),
  ]);

  assert.equal(sources.length, 1);
  assert.deepEqual(sources[0].usedInSections.sort(), ['background_theory', 'result']);
});

test('SourceRecord citation generation includes website accessedAt', () => {
  const citation = sourceRecordToCitationText(
    makeSource({ sourceType: 'website', accessedAt: '2026-04-25', url: 'https://example.test' }),
  );

  assert.match(citation, /accessed 2026-04-25/);
});

test('paper results convert into SourceRecord with safe fallbacks', () => {
  const source = convertPaperResultToSourceRecord({
    title: '',
    authors: [{ name: 'Kim' }],
    year: 2024,
    url: 'https://example.test/paper',
    source_provider: 'semantic',
  });

  assert.equal(source.title, '제목 미상');
  assert.deepEqual(source.authors, ['Kim']);
  assert.equal(source.year, '2024');
  assert.equal(source.sourceType, 'paper');
  assert.equal(source.reliability, 'high');
});

test('citation style builders generate korean school, apa, and simple url text', () => {
  const source = makeSource({ sourceType: 'website', accessedAt: '2026-04-25' });

  assert.match(buildCitationText(source, 'korean_school'), /접속일: 2026-04-25/);
  assert.match(buildCitationText(source, 'apa'), /accessed 2026-04-25/);
  assert.match(buildCitationText(source, 'simple_url'), /https:\/\/example\.test\/source/);
});

test('sources can be grouped by section and rendered as references markdown', () => {
  const sources = [
    makeSource({ id: 'a', title: 'A Source', usedInSections: ['background_theory'] }),
    makeSource({ id: 'b', title: 'B Source', url: 'https://example.test/b', usedInSections: ['result'] }),
  ];
  const grouped = groupSourcesBySection(sources);
  const markdown = buildReferencesMarkdown(sources, createDefaultReportFormatProfile());

  assert.equal(grouped.background_theory.length, 1);
  assert.equal(grouped.result.length, 1);
  assert.match(markdown, /1\./);
  assert.match(markdown, /A Source|B Source/);
});

test('FormatPatch cannot modify body content', () => {
  const result = validateReportPatch(
    {
      type: 'format',
      patchId: 'format-1',
      target: 'typography',
      changes: { body: 'replace this' },
      rationale: 'bad patch',
      requiresApproval: true,
      status: 'pending',
    },
    createInitialReportDocumentState(),
  );

  assert.equal(result.valid, false);
  assert.match(result.errors.join('\n'), /본문/);
});

test('ReportFormatProfile default preserves standard research constraints', () => {
  const profile = createDefaultReportFormatProfile();

  assert.equal(profile.templateId, 'standard_research');
  assert.equal(profile.numbering.chapter, 'roman');
  assert.equal(profile.numbering.subsection, 'decimal');
  assert.equal(profile.numbering.useTableOfContents, true);
  assert.equal(profile.citation.required, true);
  assert.equal(profile.typography.bodyFontSizePt, 11);
  assert.equal(profile.typography.lineHeight, 1.5);
  assert.equal(profile.math.renderer, 'latex_katex');
  assert.equal(profile.figures.requireCaption, true);
  assert.equal(profile.figures.requireSource, true);
});

test('validateReportPatch catches figure without source metadata', () => {
  const patch: ContentPatch = {
    type: 'content',
    patchId: 'content-figure',
    targetSection: 'result',
    action: 'append',
    contentBlocks: [
      {
        type: 'figure',
        imageUrl: 'https://example.test/figure.png',
        caption: '',
        altText: '',
        sourceId: '',
      },
    ],
    contentMarkdown: '',
    sourceIds: [],
    selectedCandidateIds: [],
    rationale: 'Add figure',
    evidenceBoundaryNote: '',
    requiresApproval: true,
    status: 'pending',
  };
  const result = validateReportPatch(patch, createInitialReportDocumentState());

  assert.equal(result.valid, false);
  assert.match(result.errors.join('\n'), /caption/);
  assert.match(result.errors.join('\n'), /sourceId/);
});

test('source coverage warns when factual section patch lacks sourceIds', () => {
  const patch: ContentPatch = {
    type: 'content',
    patchId: 'factual-no-source',
    targetSection: 'background_theory',
    action: 'append',
    contentBlocks: [
      {
        type: 'paragraph',
        text: '연구에 따르면 투수블록은 도시 침수 저감에 영향을 미친다.',
      },
    ],
    sourceIds: [],
    selectedCandidateIds: [],
    rationale: 'Need evidence',
    evidenceBoundaryNote: '',
    requiresApproval: true,
    status: 'pending',
  };
  const result = validateSourceCoverage(patch, createInitialReportDocumentState());

  assert.equal(result.valid, true);
  assert.match(result.warnings.join('\n'), /sourceIds|출처/);
});

test('motivation section can contain personal interpretation without source error', () => {
  const patch: ContentPatch = {
    type: 'content',
    patchId: 'motivation-personal',
    targetSection: 'motivation',
    action: 'append',
    contentBlocks: [{ type: 'paragraph', text: '도시 침수를 보며 이 주제를 탐구하고 싶어졌다.' }],
    sourceIds: [],
    selectedCandidateIds: [],
    rationale: 'Personal motivation',
    evidenceBoundaryNote: '',
    requiresApproval: true,
    status: 'pending',
  };
  const result = validateSourceCoverage(patch, createInitialReportDocumentState());

  assert.equal(result.errors.length, 0);
});

test('math and figure utilities detect unsafe blocks', () => {
  const math = validateLatexSyntaxBasic('');
  const figure = validateFigureBlock({
    type: 'figure',
    imageUrl: '',
    caption: '',
    sourceId: '',
    altText: '',
  });

  assert.equal(math.valid, false);
  assert.match(math.errors.join('\n'), /LaTeX/);
  assert.equal(figure.valid, false);
  assert.match(figure.errors.join('\n'), /caption/);
});

test('research intent rules infer query and target section', () => {
  const text = '이론적 배경에 넣을 도시 침수랑 투수블록 관련 논문 찾아줘';

  assert.equal(isResearchRequestMessage(text), true);
  assert.equal(inferTargetSectionFromResearchMessage(text), 'background_theory');
  assert.match(buildResearchQueryFromMessage(text, { selectedTopic: '투수블록과 침수', targetMajor: '건축학과' }), /투수블록/);
});

test('validateReportBeforeExport detects broken roman section order', () => {
  const documentState = createInitialReportDocumentState({
    metadata: {
      title: 'Valid title',
      subtitle: '',
      schoolName: '',
      grade: '',
      className: '',
      studentName: '',
      studentId: '',
      teacherName: '',
      date: '',
      targetMajor: '',
      targetUniversity: '',
    },
    sectionOrder: ['result', 'motivation', 'background_theory', 'research_method', 'conclusion', 'references'],
  });

  const result = validateReportBeforeExport(documentState);
  assert.equal(result.valid, false);
  assert.match(result.errors.join('\n'), /로마숫자/);
});

test('structured draft can be projected into ReportDocumentState for validation', () => {
  const structuredDraft = makeStructuredDraftWithStudentContent();
  const documentState = structuredDraftToReportDocumentState(structuredDraft);

  assert.match(documentState.sections.cover.studentAuthoredText || '', /student sentence/);
});

test('ChoiceCardGroup renders card, chip, and button styles from guided choice groups', () => {
  const baseGroup = {
    id: 'topic-selection',
    title: 'Choose one',
    options: [{ id: 'topic-1', label: 'Topic one', description: 'A focused option', value: 'topic-1' }],
  };

  const cardMarkup = renderToStaticMarkup(
    React.createElement(ChoiceCardGroup, {
      group: { ...baseGroup, style: 'cards' },
      onSelect: () => undefined,
    }),
  );
  const chipMarkup = renderToStaticMarkup(
    React.createElement(ChoiceCardGroup, {
      group: { ...baseGroup, style: 'chips' },
      onSelect: () => undefined,
    }),
  );
  const buttonMarkup = renderToStaticMarkup(
    React.createElement(ChoiceCardGroup, {
      group: { ...baseGroup, style: 'buttons' },
      onSelect: () => undefined,
    }),
  );

  assert.match(cardMarkup, /Topic one/);
  assert.match(chipMarkup, /rounded-full/);
  assert.match(buttonMarkup, /sm:grid-cols-2/);
});

test('PatchReviewCard disables apply when validation has errors', () => {
  const reportPatch = convertWorkshopDraftPatchToReportPatch(makeWorkshopPatch());
  const markup = renderToStaticMarkup(
    React.createElement(PatchReviewCard, {
      patch: reportPatch,
      validation: {
        valid: false,
        errors: ['학생 작성 내용을 자동으로 교체할 수 없습니다.'],
        warnings: [],
        autoFixes: [],
      },
      onApply: () => undefined,
      onReject: () => undefined,
    }),
  );

  assert.match(markup, /적용 전 수정 필요/);
  assert.match(markup, /disabled/);
});

function makeWorkshopPatch(): WorkshopDraftPatchProposal {
  return {
    mode: 'section_drafting',
    block_id: 'body_section_1',
    heading: 'Background',
    content_markdown: 'This is the first draft paragraph based on the selected idea.',
    rationale: 'The student selected this direction.',
    evidence_boundary_note: 'Needs a verified source before export.',
    requires_approval: true,
  };
}

function makeStructuredDraftWithStudentContent(): WorkshopStructuredDraftState {
  const draft = createEmptyStructuredDraft('section_drafting');
  draft.blocks = draft.blocks.map((block) =>
    block.block_id === 'title'
      ? {
          ...block,
          content_markdown: Array.from({ length: 30 }, (_, index) => `student sentence ${index + 1}`).join(' '),
          attribution: 'student-authored',
        }
      : block,
  );
  return draft;
}

function makeSource(overrides: Partial<SourceRecord> = {}): SourceRecord {
  return {
    id: 'source-a',
    title: 'Shared Source',
    authors: ['Kim'],
    year: '2026',
    publisher: 'Publisher',
    journal: '',
    url: 'https://example.test/source',
    accessedAt: '',
    sourceType: 'paper',
    reliability: 'high',
    usedInSections: [],
    citationText: '',
    ...overrides,
  };
}
