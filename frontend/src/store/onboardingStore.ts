import { create } from 'zustand';
import type {
  OnboardingGoalsUpdateRequest,
  OnboardingGoalsUpdateResponse,
  OnboardingProfileUpdateRequest,
  OnboardingProfileUpdateResponse,
} from '@shared-contracts';
import { api } from '../lib/api';
import { auth } from '../lib/firebase';
import { isGuestSessionActive, updateGuestProfile, updateGuestTargets } from '../lib/guestProfile';
import { updateLocalAuthProfile, updateLocalAuthTargets } from '../lib/localAuthProfile';
import { useAuthStore } from './authStore';

export interface ProfileData {
  grade: string;
  track: string;
  career: string;
}

export interface GoalsData {
  target_university: string;
  target_major: string;
  admission_type: string;
  interest_universities: string[];
}

interface OnboardingState {
  step: number;
  profile: ProfileData;
  goals: GoalsData;
  isLoading: boolean;
  error: string | null;

  setStep: (step: number) => void;
  setProfile: (data: Partial<ProfileData>) => void;
  setGoals: (data: Partial<GoalsData>) => void;
  submitProfile: () => Promise<boolean>;
  submitGoals: (directData?: GoalsData) => Promise<boolean>;
  reset: () => void;
}

const initialProfile: ProfileData = { grade: '', track: '', career: '' };
const initialGoals: GoalsData = {
  target_university: '',
  target_major: '',
  admission_type: '',
  interest_universities: [],
};

export const useOnboardingStore = create<OnboardingState>((set, get) => ({
  step: 1,
  profile: initialProfile,
  goals: initialGoals,
  isLoading: false,
  error: null,

  setStep: (step) => set({ step, error: null }),

  setProfile: (data) => set((state) => ({ profile: { ...state.profile, ...data } })),

  setGoals: (data) => set((state) => ({ goals: { ...state.goals, ...data } })),

  submitProfile: async () => {
    set({ isLoading: true, error: null });
    try {
      const { profile } = get();
      const payload: OnboardingProfileUpdateRequest = profile;

      if (isGuestSessionActive()) {
        const updatedUser = updateGuestProfile(payload, useAuthStore.getState().user);
        useAuthStore.getState().setUser(updatedUser);
        set({ step: 2, isLoading: false });
        return true;
      }

      const updatedUser = await api.post<OnboardingProfileUpdateResponse>('/api/v1/users/onboarding/profile', payload);
      useAuthStore.getState().setUser(updatedUser);
      set({ step: 2, isLoading: false });
      return true;
    } catch (err: any) {
      if (isGuestSessionActive()) {
        const { profile } = get();
        const updatedUser = updateGuestProfile(profile, useAuthStore.getState().user);
        useAuthStore.getState().setUser(updatedUser);
        set({ step: 2, isLoading: false });
        return true;
      }
      const currentAuthUser = auth?.currentUser;
      if (currentAuthUser) {
        const { profile } = get();
        const updatedUser = updateLocalAuthProfile(profile, currentAuthUser, useAuthStore.getState().user);
        useAuthStore.getState().setUser(updatedUser);
        set({ step: 2, isLoading: false });
        return true;
      }
      set({ error: err.response?.data?.detail || '프로필 저장에 실패했습니다. 다시 시도해주세요.', isLoading: false });
      return false;
    }
  },

  submitGoals: async (directData?: GoalsData) => {
    set({ isLoading: true, error: null });
    try {
      const goals = directData || get().goals;
      const payload: OnboardingGoalsUpdateRequest = goals;

      if (isGuestSessionActive()) {
        const updatedUser = updateGuestTargets(payload, useAuthStore.getState().user);
        useAuthStore.getState().setUser(updatedUser);
        set({ isLoading: false });
        return true;
      }

      const updatedUser = await api.post<OnboardingGoalsUpdateResponse>('/api/v1/users/onboarding/goals', payload);
      useAuthStore.getState().setUser(updatedUser);
      set({ isLoading: false });
      return true;
    } catch (err: any) {
      if (isGuestSessionActive()) {
        const goals = directData || get().goals;
        const updatedUser = updateGuestTargets(goals, useAuthStore.getState().user);
        useAuthStore.getState().setUser(updatedUser);
        set({ isLoading: false });
        return true;
      }
      const currentAuthUser = auth?.currentUser;
      if (currentAuthUser) {
        const goals = directData || get().goals;
        const updatedUser = updateLocalAuthTargets(goals, currentAuthUser, useAuthStore.getState().user);
        useAuthStore.getState().setUser(updatedUser);
        set({ isLoading: false });
        return true;
      }
      set({ error: err.response?.data?.detail || '목표 저장에 실패했습니다. 다시 시도해주세요.', isLoading: false });
      return false;
    }
  },

  reset: () => set({ step: 1, profile: initialProfile, goals: initialGoals, error: null, isLoading: false }),
}));
