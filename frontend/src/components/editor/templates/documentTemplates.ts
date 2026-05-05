import type {
  DocumentTemplateDefinition,
  DocumentTemplateSection,
  UniFoliDocumentTemplateId,
} from '../model/documentModel';

const BASIC_SECTIONS: DocumentTemplateSection[] = [
  { id: 'title', title: '제목', description: '보고서 제목과 핵심 탐구 방향을 정리합니다.', defaultBody: '탐구 주제를 한 문장으로 분명하게 적어 주세요.' },
  { id: 'motivation', title: '탐구 동기', description: '개인적 관심과 사회적 필요를 연결합니다.', defaultBody: '기존 활동에서 출발한 문제의식과 이 주제를 선택한 이유를 적어 주세요.' },
  { id: 'topic', title: '탐구 주제', description: '연구 질문과 탐구 범위를 정합니다.', defaultBody: '연구 질문, 가설 또는 탐구 관점을 구체화해 주세요.' },
  { id: 'background', title: '탐구 배경', description: '필요한 개념과 자료를 정리합니다.', defaultBody: '핵심 개념, 선행 자료, 출처가 필요한 사실 주장을 분리해 주세요.' },
  { id: 'method', title: '탐구 방법', description: '실험, 조사, 데이터 분석 절차를 설계합니다.', defaultBody: '변수, 자료 수집 방식, 분석 기준, 안전 유의사항을 적어 주세요.' },
  { id: 'process', title: '탐구 과정', description: '실제 수행 과정과 판단 근거를 남깁니다.', defaultBody: '단계별 진행 과정, 시행착오, 보완한 점을 정리해 주세요.' },
  { id: 'result', title: '탐구 결과', description: '결과와 해석을 구분합니다.', defaultBody: '확인된 결과, 예상 분석, 한계를 구분해서 작성해 주세요.' },
  { id: 'reflection', title: '느낀 점 및 진로 연계', description: '성장 서사와 후속 탐구를 연결합니다.', defaultBody: '탐구 전후로 관점이 어떻게 바뀌었는지와 진로 연결점을 적어 주세요.' },
  { id: 'references', title: '참고문헌', description: '본문 인용과 참고문헌을 정리합니다.', defaultBody: '출처 관리 패널에서 참고문헌을 자동 업데이트할 수 있습니다.' },
];

const ACADEMIC_SECTIONS: DocumentTemplateSection[] = [
  { id: 'title', title: '제목', description: '논문형 제목과 연구 범위를 정합니다.', defaultBody: '핵심 변수, 대상, 방법이 드러나는 제목을 적어 주세요.' },
  { id: 'abstract', title: '초록', description: '문제, 방법, 결과 방향, 의의를 짧게 요약합니다.', defaultBody: '아직 실제 결과가 없다면 연구 설계와 예상 분석 범위 중심으로 작성해 주세요.' },
  { id: 'keywords', title: '키워드', description: '검색 가능한 핵심어를 정리합니다.', defaultBody: '키워드 3~5개를 쉼표로 구분해 주세요.' },
  { id: 'introduction', title: '서론', description: '문제의식과 연구 질문을 제시합니다.', defaultBody: '개인적 관심, 사회적 필요, 전공 적합성을 연결해 주세요.' },
  { id: 'theory', title: '이론적 배경', description: '선행 개념과 출처 기반 근거를 정리합니다.', defaultBody: '사실 주장에는 인용 표시를 붙이고 검증 필요 출처는 구분해 주세요.' },
  { id: 'hypothesis', title: '연구 문제 또는 가설', description: '검증 가능한 질문으로 좁힙니다.', defaultBody: '독립변수, 종속변수, 통제 조건 또는 분석 관점을 명확히 적어 주세요.' },
  { id: 'methodology', title: '연구 방법', description: '실험, 조사, 시뮬레이션, 데이터 분석 방법을 설명합니다.', defaultBody: '자료, 절차, 분석 지표, 안전 유의사항, 한계를 포함해 주세요.' },
  { id: 'results', title: '결과', description: '측정 결과 또는 예상 분석 방향을 제시합니다.', defaultBody: '결과를 지어내지 말고 실제 결과와 예상 결과를 구분해 주세요.' },
  { id: 'discussion', title: '논의', description: '원인, 의미, 전공 연결성을 분석합니다.', defaultBody: '결과가 갖는 의미, 대안 해석, 사회적 함의를 적어 주세요.' },
  { id: 'conclusion', title: '결론', description: '핵심 결론과 후속 방향을 정리합니다.', defaultBody: '탐구 역량, 자기주도성, 성장 가능성이 드러나도록 정리해 주세요.' },
  { id: 'limitations', title: '한계점 및 후속 연구', description: '검증 한계와 다음 탐구를 제안합니다.', defaultBody: '자료 한계, 실험 한계, 개선 가능한 후속 질문을 적어 주세요.' },
  { id: 'references', title: '참고문헌', description: '선택한 인용 스타일에 맞춰 정리합니다.', defaultBody: '출처 관리 패널에서 자동 업데이트할 수 있습니다.' },
  { id: 'appendix', title: '부록', description: '표, 설문지, 계산식, 추가 자료를 보관합니다.', defaultBody: '본문 흐름을 방해하는 보조 자료를 이곳에 모아 주세요.' },
];

export const DOCUMENT_TEMPLATE_REGISTRY: Record<UniFoliDocumentTemplateId, DocumentTemplateDefinition> = {
  basic: {
    id: 'basic',
    label: '기본형 보고서',
    description: '세특, 수행평가, 고등학생 탐구보고서에 적합합니다.',
    sections: BASIC_SECTIONS,
    stylePreset: { fontFamily: 'Pretendard', bodyFontSizePt: 11, lineHeight: 1.7, headingNumbering: 'decimal' },
  },
  academic: {
    id: 'academic',
    label: '논문형 보고서',
    description: '초록, 이론적 배경, 연구 방법, 논의가 필요한 심화 탐구에 적합합니다.',
    sections: ACADEMIC_SECTIONS,
    stylePreset: { fontFamily: 'Noto Sans KR', bodyFontSizePt: 10.5, lineHeight: 1.65, headingNumbering: 'academic' },
  },
};

export function getDocumentTemplate(templateId: UniFoliDocumentTemplateId): DocumentTemplateDefinition {
  return DOCUMENT_TEMPLATE_REGISTRY[templateId] ?? DOCUMENT_TEMPLATE_REGISTRY.basic;
}

export function buildTemplateMarkdown(templateId: UniFoliDocumentTemplateId, title = ''): string {
  const template = getDocumentTemplate(templateId);
  const lines: string[] = [`# ${title.trim() || template.label}`, ''];
  let visibleIndex = 1;

  template.sections.forEach((section) => {
    if (section.id === 'title') return;
    lines.push(`## ${visibleIndex}. ${section.title}`);
    lines.push(section.defaultBody);
    lines.push('');
    visibleIndex += 1;
  });

  return lines.join('\n').trim();
}

export function convertTemplatePreservingContent(params: {
  fromMarkdown: string;
  toTemplateId: UniFoliDocumentTemplateId;
  title?: string;
}): string {
  const templateMarkdown = buildTemplateMarkdown(params.toTemplateId, params.title);
  const current = params.fromMarkdown.trim();
  if (!current) return templateMarkdown;
  return [
    templateMarkdown,
    '',
    '## 보존된 기존 초안',
    '아래 내용은 양식 전환 전에 작성된 문서입니다. 필요한 문단을 새 목차로 옮겨 정리해 주세요.',
    '',
    current,
  ].join('\n');
}
