export interface ReportTableTemplate {
  id: string;
  label: string;
  headers: string[];
  rows: string[][];
  caption: string;
}

export const REPORT_TABLE_TEMPLATES: ReportTableTemplate[] = [
  {
    id: 'experiment-conditions',
    label: '실험 조건표',
    headers: ['변수', '통제 조건', '측정 방법', '단위'],
    rows: [['독립변수', '', '', ''], ['종속변수', '', '', ''], ['통제변수', '', '', '']],
    caption: '표 1. 실험 조건 설정',
  },
  {
    id: 'experiment-results',
    label: '실험 결과표',
    headers: ['회차', '측정값', '평균', '오차', '비고'],
    rows: [['1', '', '', '', ''], ['2', '', '', '', ''], ['3', '', '', '', '']],
    caption: '표 2. 실험 결과',
  },
  {
    id: 'comparison-analysis',
    label: '비교 분석표',
    headers: ['항목', '기존 방식', '개선 방식', '차이점', '의의'],
    rows: [['', '', '', '', ''], ['', '', '', '', ''], ['', '', '', '', '']],
    caption: '표 3. 비교 분석',
  },
  {
    id: 'topic-evaluation',
    label: '탐구주제 평가표',
    headers: ['주제', '창의성', '전공 연계성', '실험 가능성', '사회적 의미', '최종 점수'],
    rows: [['', '', '', '', '', ''], ['', '', '', '', '', ''], ['', '', '', '', '', '']],
    caption: '표 4. 탐구주제 평가',
  },
];

export function tableTemplateToTiptapContent(template: ReportTableTemplate) {
  return [
    {
      type: 'table',
      content: [
        {
          type: 'tableRow',
          content: template.headers.map((header) => ({
            type: 'tableHeader',
            content: [{ type: 'paragraph', content: [{ type: 'text', text: header }] }],
          })),
        },
        ...template.rows.map((row) => ({
          type: 'tableRow',
          content: row.map((cell) => ({
            type: 'tableCell',
            content: cell ? [{ type: 'paragraph', content: [{ type: 'text', text: cell }] }] : [{ type: 'paragraph' }],
          })),
        })),
      ],
    },
    {
      type: 'paragraph',
      attrs: { textAlign: 'center' },
      content: [{ type: 'text', text: template.caption }],
    },
  ];
}
