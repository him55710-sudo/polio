import type { GuidedChoiceGroup, GuidedChoiceOption, GuidedTopicSuggestion } from '../../../lib/guidedChat';

export function buildTopicChoiceGroupFromSuggestions(
  suggestions: GuidedTopicSuggestion[],
  title = `추천 탐구 주제 ${suggestions.length}개 중 하나를 선택해 주세요.`,
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
      suggestion_type: topic.suggestion_type,
      is_starred: topic.is_starred,
      total_score: topic.total_score,
      topic_band: topic.topic_band,
      scores: topic.scores,
      record_connection_point: topic.record_connection_point,
      deepening_point: topic.deepening_point,
      career_connection_point: topic.career_connection_point,
      social_issue_connection: topic.social_issue_connection,
      experiment_or_survey_method: topic.experiment_or_survey_method,
      admissions_strength: topic.admissions_strength,
      risk_or_supplement: topic.risk_or_supplement,
    } as any)),
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
