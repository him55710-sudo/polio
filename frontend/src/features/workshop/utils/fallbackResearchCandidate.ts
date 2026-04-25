import type { 
  ResearchCandidate, 
  SourceRecord, 
  UniFoliReportSectionId 
} from '../types/reportDocument';

/**
 * Builds basic ResearchCandidates from sources when AI summary generation fails or is limited.
 */
export function buildBasicResearchCandidatesFromSources(
  sources: SourceRecord[],
  targetSection: UniFoliReportSectionId = 'prior_research'
): ResearchCandidate[] {
  // Take top 3 sources to avoid overwhelming the UI
  return sources.slice(0, 3).map((source, index) => {
    const preview = (source.metadata?.preview as string) || (source.metadata?.full_text_preview as string) || '';
    
    return {
      id: `fallback-cand-${source.id}-${index}`,
      title: source.title,
      summary: preview 
        ? `${preview.slice(0, 200)}...` 
        : `${source.publisher || '제공처'}에서 제공하는 ${source.title} 자료입니다.`,
      sectionTarget: targetSection,
      whyUseful: '검색 결과에서 발견된 신뢰할 수 있는 자료입니다.',
      sourceIds: [source.id],
      confidence: source.reliability === 'high' ? 'medium' : 'low',
      cautionNote: 'AI 요약이 제한되어 기본 자료 후보만 표시합니다.'
    };
  });
}
