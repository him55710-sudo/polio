export const DIAGNOSIS_RISK_LEVEL_VALUES = ['safe', 'warning', 'danger'] as const;
export const DIAGNOSIS_GAP_DIFFICULTY_VALUES = ['low', 'medium', 'high'] as const;
export const DIAGNOSIS_QUEST_PRIORITY_VALUES = ['low', 'medium', 'high'] as const;

export type DiagnosisRiskLevel = (typeof DIAGNOSIS_RISK_LEVEL_VALUES)[number];
export type DiagnosisGapDifficulty = (typeof DIAGNOSIS_GAP_DIFFICULTY_VALUES)[number];
export type DiagnosisQuestPriority = (typeof DIAGNOSIS_QUEST_PRIORITY_VALUES)[number];

export interface DiagnosisCitation {
  id?: string | null;
  document_id?: string | null;
  document_chunk_id?: string | null;
  provenance_type?: string;
  source_label: string;
  page_number?: number | null;
  excerpt: string;
  relevance_score: number;
}

export interface DiagnosisPolicyFlag {
  id: string;
  code: string;
  severity: string;
  detail: string;
  matched_text: string;
  match_count: number;
  status: string;
  created_at?: string | null;
}

export interface DiagnosisGap {
  title: string;
  description: string;
  difficulty: DiagnosisGapDifficulty;
}

export interface DiagnosisQuest {
  title: string;
  description: string;
  priority: DiagnosisQuestPriority;
}

export interface DiagnosisResultPayload {
  headline: string;
  strengths: string[];
  gaps: string[];
  detailed_gaps?: DiagnosisGap[];
  recommended_focus: string;
  action_plan?: DiagnosisQuest[];
  risk_level: DiagnosisRiskLevel;
  citations?: DiagnosisCitation[];
  policy_codes?: string[];
  review_required?: boolean;
  response_trace_id?: string | null;
}

export interface StoredDiagnosis {
  major: string;
  projectId?: string;
  savedAt: string;
  diagnosis: Pick<
    DiagnosisResultPayload,
    'headline' | 'strengths' | 'gaps' | 'risk_level' | 'recommended_focus'
  >;
}

export interface DiagnosisRunRequest {
  project_id: string;
}

export interface DiagnosisRunResponse {
  id: string;
  project_id: string;
  status: string;
  result_payload: DiagnosisResultPayload | null;
  error_message: string | null;
  review_required: boolean;
  policy_flags: DiagnosisPolicyFlag[];
  citations: DiagnosisCitation[];
  response_trace_id: string | null;
  async_job_id: string | null;
  async_job_status: string | null;
}

export interface AsyncJobRead {
  id: string;
  project_id: string | null;
  job_type: string;
  resource_type: string;
  resource_id: string;
  status: string;
  retry_count: number;
  max_retries: number;
  failure_reason: string | null;
  failure_history: Array<Record<string, unknown>>;
  next_attempt_at: string;
  started_at: string | null;
  completed_at: string | null;
  dead_lettered_at: string | null;
  created_at: string;
  updated_at: string;
}
