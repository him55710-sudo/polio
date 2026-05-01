import React, { createContext, useContext, useEffect, useState } from 'react';
import { useOnboardingStore } from '../store/onboardingStore';
import { useAuthStore } from '../store/authStore';
import {
  AuthError,
  User,
  onAuthStateChanged,
  signInAnonymously,
  signInWithPopup,
  signInWithRedirect,
  signOut,
} from 'firebase/auth';
import { auth, googleProvider, isFirebaseConfigured, isGuestModeAllowed } from '../lib/firebase';
import { api } from '../lib/api';
import { clearAppAccessToken, hasAppAccessToken } from '../lib/appAccessToken';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isGuestSession: boolean;
  guestModeAvailable: boolean;
  isAuthenticated: boolean;
  isVerified: boolean;
  signInWithGoogle: () => Promise<void>;
  signInWithKakao: () => Promise<void>;
  signInWithNaver: () => Promise<void>;
  signInAsGuest: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const GUEST_SESSION_KEY = 'uni_foli_guest_session';
type SocialProvider = 'google' | 'kakao' | 'naver';
const allowLocalBackendBypass = Boolean(import.meta.env.DEV);

const POPUP_FALLBACK_ERROR_CODES = new Set([
  'auth/popup-blocked',
  'auth/popup-closed-by-user',
  'auth/cancelled-popup-request',
  'auth/operation-not-supported-in-this-environment',
]);

const GOOGLE_SOCIAL_REDIRECT_ERROR_CODES = new Set([
  'auth/configuration-not-found',
  'auth/operation-not-allowed',
  'auth/admin-restricted-operation',
  'auth/unauthorized-domain',
  'auth/invalid-api-key',
]);

const SOCIAL_LOGIN_ERROR_MESSAGE_MAP: Record<string, string> = {
  'Social login is disabled.': '현재 백엔드에서 소셜 로그인이 비활성화되어 있어요. AUTH_SOCIAL_LOGIN_ENABLED=true로 설정해 주세요.',
  'Social login is not configured.': '소셜 로그인 보안 설정이 누락되었어요. AUTH_SOCIAL_STATE_SECRET을 설정해 주세요.',
  'Google login is not configured.': 'Google OAuth 설정이 누락되었어요. GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET을 확인해 주세요.',
  'Google login provider request failed.': 'Google 인증 서버와 통신에 실패했어요. 잠시 후 다시 시도해 주세요.',
  'Kakao login provider request failed.': '카카오 인증 서버와 통신에 실패했어요. 잠시 후 다시 시도해 주세요.',
  'Naver login provider request failed.': '네이버 인증 서버와 통신에 실패했어요. 잠시 후 다시 시도해 주세요.',
};

function extractApiErrorMessage(error: unknown): string | null {
  const responseData = (error as { response?: { data?: { detail?: unknown } } })?.response?.data;
  if (typeof responseData?.detail === 'string' && responseData.detail.trim()) {
    const detail = responseData.detail.trim();
    return SOCIAL_LOGIN_ERROR_MESSAGE_MAP[detail] ?? detail;
  }
  return null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [guestSessionActive, setGuestSessionActive] = useState(false);
  const guestModeAvailable = isGuestModeAllowed;
  const backendSessionAuthenticated = useAuthStore(state => state.isAuthenticated);

  useEffect(() => {
    const hasExistingGuestSession = localStorage.getItem(GUEST_SESSION_KEY) === '1';
    if (hasExistingGuestSession) {
      setGuestSessionActive(true);
    }

    if (!auth || !isFirebaseConfigured) {
      if (hasAppAccessToken()) {
        void useAuthStore.getState().fetchProfile().finally(() => setLoading(false));
        return;
      }
      if (allowLocalBackendBypass) {
        void useAuthStore.getState().fetchProfile().finally(() => setLoading(false));
        return;
      }
      useAuthStore.getState().setUser(null);
      setLoading(false);
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        clearAppAccessToken();
        const shouldMarkGuest = currentUser.isAnonymous;
        setGuestSessionActive(shouldMarkGuest);
        if (shouldMarkGuest) {
          localStorage.setItem(GUEST_SESSION_KEY, '1');
        } else {
          localStorage.removeItem(GUEST_SESSION_KEY);
        }

        await useAuthStore.getState().fetchProfile();
        useOnboardingStore.getState().syncWithUser(useAuthStore.getState().user);
      } else {
        // Check for local guest session even if Firebase user is null
        const localGuestActive = localStorage.getItem(GUEST_SESSION_KEY) === '1';

        if (hasAppAccessToken() || allowLocalBackendBypass || localGuestActive) {
          await useAuthStore.getState().fetchProfile();
          useOnboardingStore.getState().syncWithUser(useAuthStore.getState().user);
        } else {
          useAuthStore.getState().setUser(null);
        }
      }
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  const signInWithSocialRedirect = async (provider: SocialProvider) => {
    try {
      const response = await api.post<{ authorize_url: string }>('/api/v1/auth/social/prepare', {
        provider,
      });
      window.location.href = response.authorize_url;
    } catch (error) {
      const detail = extractApiErrorMessage(error);
      if (detail) {
        throw new Error(detail);
      }
      throw error;
    }
  };

  const signInWithGoogle = async () => {
    const canUseFirebaseGoogle = Boolean(auth && isFirebaseConfigured && googleProvider);
    if (canUseFirebaseGoogle) {
      try {
        await signInWithPopup(auth, googleProvider);
        return;
      } catch (error) {
        const authError = error as Partial<AuthError>;
        if (authError.code && POPUP_FALLBACK_ERROR_CODES.has(authError.code)) {
          await signInWithRedirect(auth, googleProvider);
          return;
        }
        if (authError.code && GOOGLE_SOCIAL_REDIRECT_ERROR_CODES.has(authError.code)) {
          await signInWithSocialRedirect('google');
          return;
        }
        throw error;
      }
    }

    await signInWithSocialRedirect('google');
  };

  const signInWithKakao = async () => {
    try {
      await signInWithSocialRedirect('kakao');
    } catch (error) {
      console.error('Kakao auth prepare failed:', error);
      throw error;
    }
  };

  const signInWithNaver = async () => {
    try {
      await signInWithSocialRedirect('naver');
    } catch (error) {
      console.error('Naver auth prepare failed:', error);
      throw error;
    }
  };

  const signInAsGuest = async () => {
    if (!guestModeAvailable) {
      throw new Error('Guest mode is disabled in this environment.');
    }

    try {
      if (auth && isFirebaseConfigured) {
        await signInAnonymously(auth);
        // onAuthStateChanged will handle profile fetching
      } else {
        // Local-only guest mode fallback
        setGuestSessionActive(true);
        localStorage.setItem(GUEST_SESSION_KEY, '1');
        await useAuthStore.getState().fetchProfile();
        useOnboardingStore.getState().syncWithUser(useAuthStore.getState().user);
      }
    } catch (error) {
      console.error('Firebase anonymous sign-in failed, falling back to local guest session:', error);
      // Always ensure guest session is active locally if guest mode is allowed
      setGuestSessionActive(true);
      localStorage.setItem(GUEST_SESSION_KEY, '1');
      await useAuthStore.getState().fetchProfile();
      useOnboardingStore.getState().syncWithUser(useAuthStore.getState().user);
    }
  };

  const logout = async () => {
    setGuestSessionActive(false);
    localStorage.removeItem(GUEST_SESSION_KEY);
    clearAppAccessToken();
    useAuthStore.getState().setUser(null);
    try {
      if (auth?.currentUser) {
        await signOut(auth);
      }
    } catch (error) {
      console.error('Error signing out', error);
    }
  };

  const isAuthenticated = (Boolean(user) && !user?.isAnonymous) || backendSessionAuthenticated;
  const isGuestSession =
    Boolean(user?.isAnonymous) ||
    guestSessionActive ||
    (guestModeAvailable && !isAuthenticated && !!localStorage.getItem(GUEST_SESSION_KEY));
  const isVerified = isAuthenticated;

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isGuestSession,
        guestModeAvailable,
        isAuthenticated,
        isVerified,
        signInWithGoogle,
        signInWithKakao,
        signInWithNaver,
        signInAsGuest,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
