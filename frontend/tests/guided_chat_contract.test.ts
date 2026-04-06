import assert from 'node:assert/strict';
import test from 'node:test';

import {
  applyTopicSelectionToUiState,
  createInitialGuidedChatUiState,
  type GuidedTopicSelectionResponse,
} from '../src/lib/guidedChat';

test('clicking a topic updates the right-side draft panel with starter draft markdown', () => {
  const initialState = createInitialGuidedChatUiState('# 기존 초안');

  const selectionResponse: GuidedTopicSelectionResponse = {
    selected_topic_id: 'topic-2',
    selected_title: '수학 개념을 기존 활동에 재연결하는 탐구 보고서',
    recommended_page_ranges: [
      {
        label: '균형형',
        min_pages: 3,
        max_pages: 4,
        why_this_length: '주제 배경, 근거, 성찰을 균형 있게 담기 좋습니다.',
      },
    ],
    recommended_outline: [
      {
        title: '1. 주제와 문제의식',
        purpose: '선택한 주제의 필요성과 현재 질문을 간결히 제시합니다.',
      },
    ],
    starter_draft_markdown: '# 새 스타터 초안\n\n## 1. 주제와 문제의식\n...',
    guidance_message: "선택하신 주제는 '수학 개념을 기존 활동에 재연결하는 탐구 보고서'입니다.",
  };

  const nextState = applyTopicSelectionToUiState(initialState, selectionResponse);

  assert.equal(nextState.selectedTopicId, 'topic-2');
  assert.equal(nextState.selectedTitle, selectionResponse.selected_title);
  assert.equal(nextState.draftMarkdown, selectionResponse.starter_draft_markdown);
  assert.equal(nextState.pageRanges.length, 1);
  assert.equal(nextState.outline.length, 1);
});
