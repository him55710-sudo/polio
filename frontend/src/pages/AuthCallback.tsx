import React, { useEffect } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { auth, isFirebaseConfigured } from '../lib/firebase';
import { signInWithCustomToken } from 'firebase/auth';
import { api } from '../lib/api';
import { motion } from 'motion/react';
import { Bot } from 'lucide-react';
import toast from 'react-hot-toast';
import { clearAppAccessToken, writeAppAccessToken } from '../lib/appAccessToken';
import { useAuthStore } from '../store/authStore';

const SOCIAL_LOGIN_ERROR_MESSAGE_MAP: Record<string, string> = {
  'Social login could not be completed.': '로그인 토큰을 만들지 못했어요. 잠시 후 다시 시도해 주세요.',
  'Google login provider request failed.': 'Google 인증 서버와 통신에 실패했어요. 잠시 후 다시 시도해 주세요.',
  'Kakao login provider request failed.': '카카오 인증 서버와 통신에 실패했어요. 잠시 후 다시 시도해 주세요.',
  'Naver login provider request failed.': '네이버 인증 서버와 통신에 실패했어요. 잠시 후 다시 시도해 주세요.',
  'Google code exchange failed.': 'Google 로그인 코드 교환에 실패했어요. 다시 로그인해 주세요.',
  'Invalid OAuth state.': '로그인 세션이 만료되었거나 유효하지 않아요. 다시 로그인해 주세요.',
};

function extractApiErrorMessage(error: unknown): string | null {
  const responseData = (error as { response?: { data?: { detail?: unknown } } })?.response?.data;
  if (typeof responseData?.detail === 'string' && responseData.detail.trim()) {
    const detail = responseData.detail.trim();
    return SOCIAL_LOGIN_ERROR_MESSAGE_MAP[detail] ?? detail;
  }
  return null;
}

export function AuthCallback() {
  const { provider } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');

    if (code && state && provider) {
      void handleSocialLogin(provider, code, state);
    }
  }, [provider, searchParams]);

  const handleSocialLogin = async (providerName: string, code: string, state: string) => {
    try {
      const response = await api.post<{ firebase_custom_token?: string | null; app_access_token?: string | null }>(
        '/api/v1/auth/social',
        {
          provider: providerName,
          code,
          state,
        },
      );

      const firebaseToken = response.firebase_custom_token?.trim();
      const appAccessToken = response.app_access_token?.trim();
      let signedIn = false;

      if (firebaseToken && auth && isFirebaseConfigured) {
        await signInWithCustomToken(auth, firebaseToken);
        signedIn = true;
      }

      if (!signedIn && appAccessToken) {
        writeAppAccessToken(appAccessToken);
        await useAuthStore.getState().fetchProfile();
        signedIn = true;
      }

      if (!signedIn) {
        throw new Error('No usable login token was returned.');
      }

      toast.success('로그인이 완료되었습니다.');
      navigate('/app');
    } catch (error) {
      clearAppAccessToken();
      console.error('Social login failed:', error);
      const detail = extractApiErrorMessage(error);
      toast.error(detail ?? '로그인에 실패했습니다. 다시 시도해 주세요.');
      navigate('/auth');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.94 }}
        animate={{ opacity: 1, scale: 1 }}
        className="rounded-[32px] border border-slate-200 bg-white p-10 text-center shadow-xl"
      >
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-[28px] bg-[#004aad] shadow-lg shadow-[#004aad]/20">
          <Bot size={40} className="animate-pulse text-white" />
        </div>
        <h2 className="mt-6 text-2xl font-extrabold text-slate-800">로그인 정보를 확인하고 있어요.</h2>
        <p className="mt-3 text-sm font-medium text-slate-500">잠시만 기다려 주세요.</p>
      </motion.div>
    </div>
  );
}
