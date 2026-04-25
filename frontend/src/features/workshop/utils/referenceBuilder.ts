import type {
  ContentPatch,
  ReportDocumentState,
  ReportFormatProfile,
  SourceRecord,
} from '../types/reportDocument';
import {
  buildCitationText,
  buildReferencesMarkdown as buildReferencesMarkdownFromSources,
  dedupeSourceRecords,
  updateSourceUsage,
} from '../adapters/sourceAdapter';

export function buildReferencesMarkdown(sources: SourceRecord[], formatProfile: ReportFormatProfile): string {
  return buildReferencesMarkdownFromSources(sources, formatProfile);
}

export function buildInlineCitation(source: SourceRecord, formatProfile: ReportFormatProfile): string {
  const style = formatProfile.citation.style;
  if (style === 'apa') {
    const author = source.authors[0] || 'Unknown author';
    return `(${author}, ${source.year || 'n.d.'})`;
  }
  if (style === 'simple_url') {
    return source.url ? `(${source.url})` : '(출처 정보 부족)';
  }
  const author = source.authors[0] || '저자 미상';
  return `(${author}, ${source.year || '연도 미상'})`;
}

export function mergeSourcesIntoDocumentState(
  documentState: ReportDocumentState,
  newSources: SourceRecord[],
): ReportDocumentState {
  const mergedSources = dedupeSourceRecords([...documentState.sources, ...newSources]);
  return {
    ...documentState,
    sources: mergedSources,
  };
}

export function updateDocumentStateSourceUsage(
  documentState: ReportDocumentState,
  sourceIds: string[],
  sectionId: ContentPatch['targetSection'],
): ReportDocumentState {
  return {
    ...documentState,
    sources: updateSourceUsage(documentState.sources, sourceIds, sectionId),
  };
}

export function updateReferencesPatch(
  sources: SourceRecord[],
  formatProfile: ReportFormatProfile,
): ContentPatch {
  const referencesMarkdown = buildReferencesMarkdown(sources, formatProfile);
  return {
    type: 'content',
    patchId: `references-${Date.now()}`,
    targetSection: 'references',
    action: 'replace',
    contentBlocks: [
      {
        type: 'paragraph',
        text: referencesMarkdown,
        sourceIds: sources.map((source) => source.id),
      },
    ],
    contentMarkdown: referencesMarkdown,
    sourceIds: sources.map((source) => source.id),
    selectedCandidateIds: [],
    rationale: '문서에 사용된 SourceRecord 목록을 기준으로 참고문헌 섹션을 갱신합니다.',
    evidenceBoundaryNote: sources.some((source) => !source.url && !source.journal && !source.publisher)
      ? '일부 출처는 서지 정보가 부족합니다. 부족한 항목은 보완이 필요합니다.'
      : '',
    requiresApproval: false,
    status: 'pending',
  };
}

export function sourceRecordsToCitationPreview(
  sources: SourceRecord[],
  formatProfile: ReportFormatProfile,
  limit = 3,
): string[] {
  return dedupeSourceRecords(sources)
    .slice(0, limit)
    .map((source) => buildCitationText(source, formatProfile.citation.style));
}
