import type { JSONContent } from '@tiptap/react';
import {
  createDefaultReportFormatProfile,
  createEmptyReportMetadata,
  type ReportFormatProfile,
  type ReportMetadata,
  type SourceRecord,
} from '../../../features/workshop/types/reportDocument';
import { sourceRecordToCitationText } from '../../../features/workshop/adapters/sourceAdapter';

export { createDefaultReportFormatProfile };

const ROMAN_SECTIONS = [
  'I. 연구 동기 및 목적',
  'II. 이론적 배경',
  'III. 연구 방법',
  'IV. 연구 결과',
  'V. 결론 및 제언',
];

export function createReportTemplateFromProfile(
  profile: ReportFormatProfile = createDefaultReportFormatProfile(),
  metadata: ReportMetadata = createEmptyReportMetadata(),
  sources: SourceRecord[] = [],
): JSONContent {
  return {
    type: 'doc',
    content: [
      ...renderCoverSection(metadata, profile),
      { type: 'horizontalRule' },
      ...renderTableOfContents(profile),
      { type: 'horizontalRule' },
      ...renderRomanNumberedSections(profile),
      { type: 'horizontalRule' },
      ...renderReferencesSection(sources, profile),
    ],
  };
}

export function renderCoverSection(metadata: ReportMetadata, profile: ReportFormatProfile): JSONContent[] {
  if (!profile.cover.enabled) {
    return [];
  }
  return [
    heading(1, '탐구 보고서', 'center'),
    paragraph(metadata.title || '[탐구 주제를 입력하세요]', 'center', true),
    paragraph(metadata.subtitle, 'center'),
    paragraph(`학교: ${metadata.schoolName || '____________'}    학년/반: ${metadata.grade || '____'} / ${metadata.className || '____'}`, 'center'),
    paragraph(`이름: ${metadata.studentName || '____________'}    학번: ${metadata.studentId || '____________'}`, 'center'),
    paragraph(`지도교사: ${metadata.teacherName || '____________'}    작성일: ${metadata.date || '____년 __월 __일'}`, 'center'),
  ];
}

export function renderTableOfContents(profile: ReportFormatProfile): JSONContent[] {
  if (!profile.numbering.useTableOfContents) {
    return [];
  }
  return [
    heading(2, '목차'),
    {
      type: 'orderedList',
      content: [...ROMAN_SECTIONS, '참고 문헌'].map((title) => ({
        type: 'listItem',
        content: [paragraph(title)],
      })),
    },
  ];
}

export function renderRomanNumberedSections(profile: ReportFormatProfile): JSONContent[] {
  const sectionTitles =
    profile.templateId === 'engineering'
      ? ['I. 연구 동기 및 목적', 'II. 이론적 배경', 'III. 실험 및 연구 방법', 'IV. 데이터 분석 및 결과', 'V. 결론 및 제언']
      : ROMAN_SECTIONS;
  return sectionTitles.flatMap((title) => [
    heading(2, title),
    paragraph('이 섹션의 핵심 내용을 작성하세요. 출처가 필요한 사실 주장은 참고문헌과 연결하세요.'),
  ]);
}

export function renderReferencesSection(sources: SourceRecord[], profile: ReportFormatProfile): JSONContent[] {
  if (!profile.citation.requireReferencesSection) {
    return [];
  }
  return [
    heading(2, '참고 문헌'),
    {
      type: 'orderedList',
      content: (sources.length ? sources.map(sourceRecordToCitationText) : ['출처를 추가하세요']).map((citation) => ({
        type: 'listItem',
        content: [paragraph(citation)],
      })),
    },
  ];
}

function heading(level: 1 | 2 | 3, text: string, textAlign?: 'left' | 'center'): JSONContent {
  return {
    type: 'heading',
    attrs: { level, ...(textAlign ? { textAlign } : {}) },
    content: text ? [{ type: 'text', text }] : undefined,
  };
}

function paragraph(text: string, textAlign?: 'left' | 'center', bold = false): JSONContent {
  return {
    type: 'paragraph',
    attrs: textAlign ? { textAlign } : undefined,
    content: text
      ? [{ type: 'text', text, ...(bold ? { marks: [{ type: 'bold' }] } : {}) }]
      : [{ type: 'text', text: '' }],
  };
}
