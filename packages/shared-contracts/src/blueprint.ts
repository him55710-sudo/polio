export const BLUEPRINT_QUEST_DIFFICULTY_VALUES = ['low', 'medium', 'high'] as const;
export const BLUEPRINT_QUEST_STATUS_VALUES = ['PENDING', 'IN_PROGRESS', 'COMPLETED'] as const;

export type BlueprintQuestDifficulty = (typeof BLUEPRINT_QUEST_DIFFICULTY_VALUES)[number];
export type BlueprintQuestStatus = (typeof BLUEPRINT_QUEST_STATUS_VALUES)[number];

export interface BlueprintQuest {
  id: string;
  subject: string;
  title: string;
  summary: string;
  difficulty: BlueprintQuestDifficulty;
  why_this_matters: string;
  expected_record_impact: string;
  recommended_output_type: string;
  status: BlueprintQuestStatus;
}

export interface BlueprintQuestGroup {
  name: string;
  quests: BlueprintQuest[];
}

export interface CurrentBlueprintResponse {
  id: string;
  project_id: string;
  project_title: string;
  target_major: string | null;
  headline: string;
  recommended_focus: string;
  semester_priority_message: string;
  priority_quests: BlueprintQuest[];
  subject_groups: BlueprintQuestGroup[];
  activity_groups: BlueprintQuestGroup[];
  expected_record_effects: string[];
  created_at: string;
}

export interface QuestStarterChoice {
  id: string;
  label: string;
  prompt: string;
}

export interface QuestStartPayload {
  quest_id: string;
  blueprint_id: string;
  project_id: string;
  project_title: string;
  target_major: string | null;
  subject: string;
  title: string;
  summary: string;
  why_this_matters: string;
  expected_record_impact: string;
  recommended_output_type: string;
  status: BlueprintQuestStatus;
  workshop_intro: string;
  document_seed_markdown: string;
  starter_choices_seed: QuestStarterChoice[];
}
