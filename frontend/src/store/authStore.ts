import { create } from 'zustand';
import { signOut } from 'firebase/auth';
import { auth } from '../lib/firebase';
import { api } from '../lib/api';
import { syncUserProfileToFirestore } from '../lib/db';
import { isGuestSessionActive, readGuestProfile } from '../lib/guestProfile';
import { buildLocalAuthProfile, readLocalAuthProfile } from '../lib/localAuthProfile';
import { clearAppAccessToken } from '../lib/appAccessToken';
import type { UserProfile } from '@shared-contracts';

interface AuthState {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: UserProfile | null) => void;
  setLoading: (isLoading: boolean) => void;
  fetchProfile: () => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  
  setUser: (user) => set({ 
    user, 
    isAuthenticated: !!user && !user.is_guest, 
    isLoading: false 
  }),
  
  setLoading: (isLoading) => set({ isLoading }),
  
  fetchProfile: async () => {
    try {
      const profile = await api.get<UserProfile>('/api/v1/users/me');
      // Backend profile normally means real auth
      set({ user: profile, isAuthenticated: true, isLoading: false });
      void syncUserProfileToFirestore(profile);

      // Sync marketing consent if pending
      const pendingConsent = localStorage.getItem('uni_foli_pending_marketing_consent');
      if (pendingConsent !== null) {
        const agreed = pendingConsent === 'true';
        try {
          await api.post('/api/v1/users/onboarding/profile', { marketing_agreed: agreed });
          localStorage.removeItem('uni_foli_pending_marketing_consent');
          const nextProfile = { ...profile, marketing_agreed: agreed };
          set((state) => ({
            user: state.user ? { ...state.user, marketing_agreed: agreed } : null
          }));
          void syncUserProfileToFirestore(nextProfile);
        } catch (err) {
          console.error('Failed to sync marketing consent:', err);
        }
      }
    } catch (error) {
      console.error('Failed to fetch user profile:', error);
      const currentAuthUser = auth?.currentUser;
      if (currentAuthUser) {
        const cachedLocalProfile = readLocalAuthProfile(currentAuthUser.uid);
        const fallbackProfile = buildLocalAuthProfile(currentAuthUser, cachedLocalProfile);
        // Firebase user exists - if anonymous, it's a guest
        const isGuest = currentAuthUser.isAnonymous;
        set({ 
          user: fallbackProfile, 
          isAuthenticated: !isGuest, 
          isLoading: false 
        });
        return;
      }

      if (isGuestSessionActive()) {
        const guestProfile = readGuestProfile();
        if (guestProfile) {
          // Explicitly NOT authenticated if it's a guest profile
          set({ user: guestProfile, isAuthenticated: false, isLoading: false });
          return;
        }
      }
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  logout: async () => {
    try {
      await signOut(auth);
      clearAppAccessToken();
      set({ user: null, isAuthenticated: false, isLoading: false });
    } catch (error) {
      console.error('Logout failed:', error);
    }
  },
}));
