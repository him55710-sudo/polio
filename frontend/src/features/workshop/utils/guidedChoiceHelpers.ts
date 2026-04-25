import type { GuidedChoiceGroup, GuidedChoiceOption, GuidedTopicSuggestion } from '../../../lib/guidedChat';

export function buildTopicChoiceGroupFromSuggestions(
  suggestions: GuidedTopicSuggestion[],
  title = '마음에 드는 탐구주제를 선택하세요.',
): GuidedChoiceGroup {
  return {
    id: 'topic-selection',
    title,
    style: 'cards',
    options: suggestions.map((topic) => ({
      id: topic.id,
      label: topic.title,
      description: topic.why_fit_student,
      value: topic.id,
    })),
  };
}

export function getChoiceValue(option: GuidedChoiceOption): string {
  return String(option.value || option.id);
}

export function isChoiceBusy(groupId: string, option: GuidedChoiceOption, selectingTopicId?: string | null): boolean {
  return groupId === 'topic-selection' && Boolean(selectingTopicId) && selectingTopicId === getChoiceValue(option);
}

export function isChoiceDisabled(
  groupId: string,
  option: GuidedChoiceOption,
  isGuidedActionLoading?: boolean,
  selectingTopicId?: string | null,
): boolean {
  return Boolean(isGuidedActionLoading || isChoiceBusy(groupId, option, selectingTopicId));
}
