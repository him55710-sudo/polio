import type { JSONContent } from '@tiptap/react';

/**
 * 탐구보고서 표준 템플릿 (Tiptap JSON)
 *
 * 섹션 구성:
 *   1. 표지 (제목, 학교, 학생명, 일자)
 *   2. 목차
 *   3. I. 연구 동기 및 목적
 *   4. II. 이론적 배경
 *   5. III. 연구 방법
 *   6. IV. 연구 결과
 *   7. V. 결론 및 제언
 *   8. 참고 문헌
 */
export function getResearchReportTemplate(): JSONContent {
  return {
    type: 'doc',
    content: [
      // ─── 표지 ───
      {
        type: 'heading',
        attrs: { level: 1, textAlign: 'center' },
        content: [{ type: 'text', text: '탐구 보고서' }],
      },
      {
        type: 'paragraph',
        attrs: { textAlign: 'center' },
        content: [
          { type: 'text', marks: [{ type: 'bold' }], text: '[탐구 주제를 여기에 입력하세요]' },
        ],
      },
      {
        type: 'paragraph',
        attrs: { textAlign: 'center' },
        content: [{ type: 'text', text: ' ' }],
      },
      {
        type: 'paragraph',
        attrs: { textAlign: 'center' },
        content: [
          { type: 'text', text: '학교: ________________    학년/반: ________________' },
        ],
      },
      {
        type: 'paragraph',
        attrs: { textAlign: 'center' },
        content: [
          { type: 'text', text: '이름: ________________    작성일: ____년 __월 __일' },
        ],
      },
      {
        type: 'paragraph',
        content: [{ type: 'text', text: ' ' }],
      },
      { type: 'horizontalRule' },

      // ─── 목차 ───
      {
        type: 'heading',
        attrs: { level: 2 },
        content: [{ type: 'text', text: '목차' }],
      },
      {
        type: 'orderedList',
        content: [
          {
            type: 'listItem',
            content: [{ type: 'paragraph', content: [{ type: 'text', text: '연구 동기 및 목적' }] }],
          },
          {
            type: 'listItem',
            content: [{ type: 'paragraph', content: [{ type: 'text', text: '이론적 배경' }] }],
          },
          {
            type: 'listItem',
            content: [{ type: 'paragraph', content: [{ type: 'text', text: '연구 방법' }] }],
          },
          {
            type: 'listItem',
            content: [{ type: 'paragraph', content: [{ type: 'text', text: '연구 결과' }] }],
          },
          {
            type: 'listItem',
            content: [{ type: 'paragraph', content: [{ type: 'text', text: '결론 및 제언' }] }],
          },
          {
            type: 'listItem',
            content: [{ type: 'paragraph', content: [{ type: 'text', text: '참고 문헌' }] }],
          },
        ],
      },
      { type: 'horizontalRule' },

      // ─── I. 연구 동기 및 목적 ───
      {
        type: 'heading',
        attrs: { level: 2 },
        content: [{ type: 'text', text: 'I. 연구 동기 및 목적' }],
      },
      {
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: '1. 연구 동기' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            marks: [{ type: 'italic' }],
            text: '이 탐구를 시작하게 된 계기와 개인적 관심사를 서술하세요. 교과 학습, 독서, 사회 이슈 등 구체적 경험을 중심으로 작성합니다.',
          },
        ],
      },
      {
        type: 'paragraph',
        content: [{ type: 'text', text: '' }],
      },
      {
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: '2. 연구 목적' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            marks: [{ type: 'italic' }],
            text: '본 탐구를 통해 알아보고자 하는 것을 구체적 연구 질문(Research Question) 형태로 기술하세요.',
          },
        ],
      },
      {
        type: 'paragraph',
        content: [{ type: 'text', text: '' }],
      },

      // ─── II. 이론적 배경 ───
      {
        type: 'heading',
        attrs: { level: 2 },
        content: [{ type: 'text', text: 'II. 이론적 배경' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            marks: [{ type: 'italic' }],
            text: '탐구 주제와 관련된 선행 연구, 이론, 개념 등을 정리하세요. 참고 문헌에 기반하여 작성하되, 출처를 명시합니다.',
          },
        ],
      },
      {
        type: 'paragraph',
        content: [{ type: 'text', text: '' }],
      },

      // ─── III. 연구 방법 ───
      {
        type: 'heading',
        attrs: { level: 2 },
        content: [{ type: 'text', text: 'III. 연구 방법' }],
      },
      {
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: '1. 연구 설계' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            marks: [{ type: 'italic' }],
            text: '어떤 방법(실험, 설문, 문헌 분석, 시뮬레이션 등)으로 연구를 수행했는지 기술하세요.',
          },
        ],
      },
      {
        type: 'paragraph',
        content: [{ type: 'text', text: '' }],
      },
      {
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: '2. 연구 대상 및 도구' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            marks: [{ type: 'italic' }],
            text: '연구 대상(표본), 사용 도구, 측정 방법 등을 구체적으로 기술하세요.',
          },
        ],
      },
      {
        type: 'paragraph',
        content: [{ type: 'text', text: '' }],
      },
      {
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: '3. 연구 절차' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            marks: [{ type: 'italic' }],
            text: '연구의 진행 순서를 단계별로 기술하세요.',
          },
        ],
      },
      {
        type: 'orderedList',
        content: [
          {
            type: 'listItem',
            content: [{ type: 'paragraph', content: [{ type: 'text', text: '1단계: ' }] }],
          },
          {
            type: 'listItem',
            content: [{ type: 'paragraph', content: [{ type: 'text', text: '2단계: ' }] }],
          },
          {
            type: 'listItem',
            content: [{ type: 'paragraph', content: [{ type: 'text', text: '3단계: ' }] }],
          },
        ],
      },

      // ─── IV. 연구 결과 ───
      {
        type: 'heading',
        attrs: { level: 2 },
        content: [{ type: 'text', text: 'IV. 연구 결과' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            marks: [{ type: 'italic' }],
            text: '연구를 통해 얻은 데이터와 분석 결과를 서술하세요. 표, 그래프, 이미지 등을 활용하면 효과적입니다.',
          },
        ],
      },
      {
        type: 'paragraph',
        content: [{ type: 'text', text: '' }],
      },
      // 결과 요약 표
      {
        type: 'table',
        content: [
          {
            type: 'tableRow',
            content: [
              { type: 'tableHeader', content: [{ type: 'paragraph', content: [{ type: 'text', text: '항목' }] }] },
              { type: 'tableHeader', content: [{ type: 'paragraph', content: [{ type: 'text', text: '결과' }] }] },
              { type: 'tableHeader', content: [{ type: 'paragraph', content: [{ type: 'text', text: '비고' }] }] },
            ],
          },
          {
            type: 'tableRow',
            content: [
              { type: 'tableCell', content: [{ type: 'paragraph', content: [{ type: 'text', text: '' }] }] },
              { type: 'tableCell', content: [{ type: 'paragraph', content: [{ type: 'text', text: '' }] }] },
              { type: 'tableCell', content: [{ type: 'paragraph', content: [{ type: 'text', text: '' }] }] },
            ],
          },
          {
            type: 'tableRow',
            content: [
              { type: 'tableCell', content: [{ type: 'paragraph', content: [{ type: 'text', text: '' }] }] },
              { type: 'tableCell', content: [{ type: 'paragraph', content: [{ type: 'text', text: '' }] }] },
              { type: 'tableCell', content: [{ type: 'paragraph', content: [{ type: 'text', text: '' }] }] },
            ],
          },
        ],
      },

      // ─── V. 결론 및 제언 ───
      {
        type: 'heading',
        attrs: { level: 2 },
        content: [{ type: 'text', text: 'V. 결론 및 제언' }],
      },
      {
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: '1. 결론' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            marks: [{ type: 'italic' }],
            text: '연구 결과를 종합하여 연구 질문에 대한 답을 서술하세요.',
          },
        ],
      },
      {
        type: 'paragraph',
        content: [{ type: 'text', text: '' }],
      },
      {
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: '2. 한계점 및 후속 연구 제언' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            marks: [{ type: 'italic' }],
            text: '이 연구의 한계를 솔직하게 반성하고, 향후 어떤 추가 연구가 가능한지 제안하세요.',
          },
        ],
      },
      {
        type: 'paragraph',
        content: [{ type: 'text', text: '' }],
      },

      // ─── 참고 문헌 ───
      { type: 'horizontalRule' },
      {
        type: 'heading',
        attrs: { level: 2 },
        content: [{ type: 'text', text: '참고 문헌' }],
      },
      {
        type: 'orderedList',
        content: [
          {
            type: 'listItem',
            content: [
              {
                type: 'paragraph',
                content: [
                  {
                    type: 'text',
                    marks: [{ type: 'italic' }],
                    text: '저자 (발행연도). 제목. 출판사/학술지명.',
                  },
                ],
              },
            ],
          },
          {
            type: 'listItem',
            content: [
              {
                type: 'paragraph',
                content: [
                  {
                    type: 'text',
                    marks: [{ type: 'italic' }],
                    text: '저자 (발행연도). 제목. 출판사/학술지명.',
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  };
}
