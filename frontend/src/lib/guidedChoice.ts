import type {
  DiagnosisExportFormat,
  DiagnosisResultPayload,
  PageCountOption,
  RecommendedDirection,
  TemplateCandidate,
  TopicCandidate,
} from './diagnosis';

export interface GuidedChoiceSelection {
  directionId: string | null;
  topicId: string | null;
  pageCount: number | null;
  format: DiagnosisExportFormat | null;
  templateId: string | null;
}

function pickFirstTopic(topicCandidates: TopicCandidate[]): string | null {
  return topicCandidates[0]?.id ?? null;
}

function pickFirstPageCount(pageCountOptions: PageCountOption[]): number | null {
  return pageCountOptions[0]?.page_count ?? null;
}

function pickPreferredFormat(direction: RecommendedDirection): DiagnosisExportFormat | null {
  return (direction.format_recommendations.find((item) => item.recommended) ?? direction.format_recommendations[0])?.format ?? null;
}

export function buildInitialGuidedSelection(diagnosis: DiagnosisResultPayload): GuidedChoiceSelection {
  const directions = diagnosis.recommended_directions ?? [];
  const defaultAction = diagnosis.recommended_default_action ?? null;
  const selectedDirection =
    directions.find((item) => item.id === defaultAction?.direction_id) ??
    directions[0] ??
    null;

  if (!selectedDirection) {
    return {
      directionId: null,
      topicId: null,
      pageCount: null,
      format: null,
      templateId: null,
    };
  }

  const topicId =
    selectedDirection.topic_candidates.find((item) => item.id === defaultAction?.topic_id)?.id ??
    pickFirstTopic(selectedDirection.topic_candidates);
  const pageCount =
    selectedDirection.page_count_options.find((item) => item.page_count === defaultAction?.page_count)?.page_count ??
    pickFirstPageCount(selectedDirection.page_count_options);
  const format =
    selectedDirection.format_recommendations.find((item) => item.format === defaultAction?.export_format)?.format ??
    pickPreferredFormat(selectedDirection);

  return {
    directionId: selectedDirection.id,
    topicId,
    pageCount,
    format,
    templateId: defaultAction?.direction_id === selectedDirection.id ? (defaultAction?.template_id ?? null) : null,
  };
}

export function resolveTemplateSelection(
  templates: TemplateCandidate[],
  {
    currentTemplateId,
    preferredTemplateId,
    recommendedTemplateIds,
  }: {
    currentTemplateId: string | null;
    preferredTemplateId: string | null;
    recommendedTemplateIds: Set<string>;
  },
): string | null {
  if (currentTemplateId && templates.some((item) => item.id === currentTemplateId)) {
    return currentTemplateId;
  }
  if (preferredTemplateId && templates.some((item) => item.id === preferredTemplateId)) {
    return preferredTemplateId;
  }
  return templates.find((item) => recommendedTemplateIds.has(item.id))?.id ?? templates[0]?.id ?? null;
}
