import React, { useEffect, useMemo, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { B2BPartnershipModal } from './B2BPartnershipModal';
import { AppFooter } from './layout/AppFooter';
import { AppSidebar } from './layout/AppSidebar';
import { AppTopbar } from './layout/AppTopbar';
import { resolveCurrentNavSection } from './layout/nav-config';
import { useAuth } from '../contexts/AuthContext';
import { useAuthStore } from '../store/authStore';
import { AppShell } from './primitives';

function isDesktopViewport() {
  return typeof window !== 'undefined' && window.innerWidth >= 768;
}

export function Layout() {
  const location = useLocation();
  const { user, isGuestSession, logout } = useAuth();
  const dbUser = useAuthStore(state => state.user);

  const [isSidebarOpen, setIsSidebarOpen] = useState(isDesktopViewport);
  const [isPartnershipModalOpen, setIsPartnershipModalOpen] = useState(false);

  useEffect(() => {
    const syncSidebarByViewport = () => {
      setIsSidebarOpen(isDesktopViewport());
    };

    syncSidebarByViewport();
    window.addEventListener('resize', syncSidebarByViewport);
    return () => window.removeEventListener('resize', syncSidebarByViewport);
  }, []);

  useEffect(() => {
    if (!isDesktopViewport()) {
      setIsSidebarOpen(false);
    }
  }, [location.pathname]);

  const hasTargets = Boolean(dbUser?.target_university && dbUser?.target_major);
  const currentSection = useMemo(() => resolveCurrentNavSection(location.pathname), [location.pathname]);
  const workflowSummary = hasTargets
    ? `${currentSection.label} 단계입니다. 현재 단계의 다음 행동을 이어서 진행해 주세요.`
    : '먼저 목표 대학과 학과를 설정하면 준비 → 분석 → 실행 흐름이 활성화됩니다.';

  const userName = user?.displayName || dbUser?.name || (isGuestSession ? '게스트' : '사용자');

  return (
    <>
      <B2BPartnershipModal isOpen={isPartnershipModalOpen} onClose={() => setIsPartnershipModalOpen(false)} />
      <AppShell
        topbar={
          <AppTopbar
            currentSectionLabel={currentSection.label}
            summary={workflowSummary}
            isSidebarOpen={isSidebarOpen}
            onToggleSidebar={() => setIsSidebarOpen(open => !open)}
            primaryGoal={
              dbUser?.target_university
                ? { university: dbUser.target_university, major: dbUser.target_major ?? '' }
                : null
            }
          />
        }
        sidebar={
          <AppSidebar
            pathname={location.pathname}
            isOpen={isSidebarOpen}
            onToggle={() => setIsSidebarOpen(open => !open)}
            onCloseMobile={() => {
              if (!isDesktopViewport()) setIsSidebarOpen(false);
            }}
            userName={userName}
            userPhotoUrl={user?.photoURL}
            isGuestSession={isGuestSession}
            onLogout={logout}
          />
        }
        overlay={
          isSidebarOpen && !isDesktopViewport() ? (
            <button
              type="button"
              aria-label="내비게이션 닫기"
              onClick={() => setIsSidebarOpen(false)}
              className="absolute inset-0 z-20 bg-slate-900/30 backdrop-blur-[1px]"
            />
          ) : null
        }
        footer={<AppFooter onOpenPartnership={() => setIsPartnershipModalOpen(true)} />}
      >
        <Outlet />
      </AppShell>
    </>
  );
}
