export interface UserProfile {
  id: string;
  firebase_uid: string;
  email: string | null;
  name: string | null;
  target_university: string | null;
  target_major: string | null;
  grade: string | null;
  track: string | null;
  career: string | null;
  admission_type: string | null;
  interest_universities: string[];
  marketing_agreed: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserTargetsUpdateRequest {
  target_university?: string | null;
  target_major?: string | null;
  admission_type?: string | null;
  interest_universities?: string[] | null;
}

export type UserTargetsUpdateResponse = UserProfile;

export interface UserStats {
  report_count: number;
  level: string;
  completion_rate: number;
}

export interface OnboardingProfileUpdateRequest {
  grade?: string | null;
  track?: string | null;
  career?: string | null;
  interest_universities?: string[] | null;
  marketing_agreed?: boolean | null;
}

export type OnboardingProfileUpdateResponse = UserProfile;
export type OnboardingGoalsUpdateRequest = UserTargetsUpdateRequest;
export type OnboardingGoalsUpdateResponse = UserProfile;
