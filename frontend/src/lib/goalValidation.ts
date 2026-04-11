import { getUniversityByName, isMajorInUniversity } from './educationCatalog';

export interface GoalSelectionLike {
  university: string;
  major: string;
}

interface GoalValidationResult {
  valid: boolean;
  message?: string;
}

export function coerceMajorForUniversity(universityName: string, majorName: string): string {
  const normalizedUniversity = universityName.trim();
  const normalizedMajor = majorName.trim();

  if (!normalizedMajor) {
    return '';
  }

  return isMajorInUniversity(normalizedUniversity, normalizedMajor) ? normalizedMajor : '';
}

export function validateGoalSelection(universityName: string, majorName: string): GoalValidationResult {
  const normalizedUniversity = universityName.trim();
  const normalizedMajor = majorName.trim();

  if (!normalizedUniversity) {
    return { valid: false, message: '대학교를 먼저 선택해 주세요.' };
  }

  if (!getUniversityByName(normalizedUniversity)) {
    return { valid: false, message: '목록에 있는 대학교를 먼저 선택해 주세요.' };
  }

  if (!normalizedMajor) {
    return { valid: false, message: '학과를 먼저 선택해 주세요.' };
  }

  if (!isMajorInUniversity(normalizedUniversity, normalizedMajor)) {
    return {
      valid: false,
      message: `${normalizedUniversity}에 실제로 개설된 학과만 선택할 수 있어요.`,
    };
  }

  return { valid: true };
}

export function hasValidGoalSelection(goal: GoalSelectionLike): boolean {
  return validateGoalSelection(goal.university, goal.major).valid;
}

export function findFirstInvalidGoal<T extends GoalSelectionLike>(goals: T[]): T | null {
  return goals.find((goal) => !hasValidGoalSelection(goal)) ?? null;
}
