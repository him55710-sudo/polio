import type { CitationStyleId, UniFoliCitationSource } from '../model/documentModel';

export function createEmptyCitationSource(): UniFoliCitationSource {
  return {
    id: `src-${Date.now()}`,
    type: 'website',
    title: '',
    authors: [],
    year: '',
    publisher: '',
    url: '',
    accessedAt: new Date().toISOString().slice(0, 10),
    doi: '',
    sourceOrigin: 'user',
    verificationStatus: 'needs_verification',
    usedInSectionIds: [],
  };
}

export function formatInlineCitation(source: UniFoliCitationSource, style: CitationStyleId, index: number): string {
  const firstAuthor = source.authors[0]?.trim() || source.publisher || source.title || '출처';
  const year = source.year || '연도 미상';
  if (style === 'numbered') return `[${index + 1}]`;
  if (style === 'mla') return `(${firstAuthor})`;
  if (style === 'chicago') return `(${firstAuthor} ${year})`;
  return `(${firstAuthor}, ${year})`;
}

export function formatBibliographyEntry(source: UniFoliCitationSource, style: CitationStyleId, index: number): string {
  const authors = source.authors.length ? source.authors.join(', ') : '저자 미상';
  const year = source.year || '연도 미상';
  const title = source.title || '제목 미상';
  const publisher = source.publisher || '발행기관 미상';
  const url = source.url ? ` ${source.url}` : '';
  const accessedAt = source.accessedAt ? ` (접속일: ${source.accessedAt})` : '';
  const doi = source.doi ? ` DOI: ${source.doi}` : '';
  const verification = source.verificationStatus === 'verified' ? '' : ' [검증 필요]';

  if (style === 'numbered') return `[${index + 1}] ${authors}. ${title}. ${publisher}, ${year}.${url}${doi}${verification}`;
  if (style === 'apa') return `${authors}. (${year}). ${title}. ${publisher}.${url}${doi}${verification}`;
  if (style === 'mla') return `${authors}. "${title}." ${publisher}, ${year}.${url}${accessedAt}${verification}`;
  if (style === 'chicago') return `${authors}. ${title}. ${publisher}, ${year}.${url}${doi}${verification}`;
  return `${authors}. 「${title}」. ${publisher}, ${year}.${url}${accessedAt}${doi}${verification}`;
}

export function buildBibliographyMarkdown(sources: UniFoliCitationSource[], style: CitationStyleId): string {
  if (!sources.length) return '아직 등록된 참고문헌이 없습니다.';
  return sources.map((source, index) => `${index + 1}. ${formatBibliographyEntry(source, style, index)}`).join('\n');
}

export function detectNeedsCitationSentences(markdown: string): string[] {
  const sentences = markdown
    .split(/(?<=[.!?。！？])\s+|\n+/)
    .map((sentence) => sentence.trim())
    .filter(Boolean);
  return sentences
    .filter((sentence) => {
      if (/\[[0-9]+\]|\([^)]*,\s*\d{4}\)/.test(sentence)) return false;
      return /(증가|감소|영향|효과|비율|통계|연구|조사|보고|데이터|평균|원인|결과)/.test(sentence);
    })
    .slice(0, 12);
}
