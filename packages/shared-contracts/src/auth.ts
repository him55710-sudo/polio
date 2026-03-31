import type { UserProfile } from './user';

export const SOCIAL_PROVIDER_VALUES = ['kakao', 'naver'] as const;

export type SocialProvider = (typeof SOCIAL_PROVIDER_VALUES)[number];

export interface SocialProviderPrepareRequest {
  provider: SocialProvider;
}

export interface SocialProviderPrepareResponse {
  provider: SocialProvider;
  state: string;
  expires_in: number;
}

export interface SocialLoginRequest {
  provider: SocialProvider;
  code: string;
  state: string;
}

export interface SocialLoginResponse {
  firebase_custom_token: string;
}

export type FirebaseExchangeResponse = UserProfile;
