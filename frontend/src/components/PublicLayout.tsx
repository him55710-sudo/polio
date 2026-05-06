import React, { useEffect, useMemo, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { ArrowRight, Menu, Search, X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { UniFoliLogo } from './UniFoliLogo';
import { buttonClassName } from './ui';
import { cn } from '../lib/cn';
import { PUBLIC_DESIGN_VARIANT_STORAGE_KEY, getPublicDesignVariant } from '../lib/publicDesignVariant';

const classicNavItems = [
  { to: '/', label: '소개' },
  { to: '/faq', label: '자주 묻는 질문' },
  { to: '/contact', label: '문의' },
];

const portalNavItems = [
  { to: '/', label: 'AI진단' },
  { to: '/auth?feature=record-card', label: '세특카드' },
  { to: '/auth?feature=research-report', label: '탐구보고서' },
  { to: '/faq', label: '리로TALK' },
  { to: '/contact', label: '구독멤버십+' },
];

function PublicNavItem({
  to,
  label,
  onClick,
  variant = 'classic',
}: {
  to: string;
  label: string;
  onClick?: () => void;
  variant?: 'classic' | 'portal';
}) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      className={({ isActive }) =>
        variant === 'portal'
          ? cn(
              'rounded-lg px-3 py-2 text-sm font-black transition-all',
              isActive
                ? 'bg-[#ffdf55] text-[#1f2a44]'
                : 'text-[#39445a] hover:bg-[#fff8d8] hover:text-[#1754c8]',
            )
          : cn(
              'rounded-2xl px-3.5 py-2.5 text-sm font-black transition-all',
              isActive
                ? 'bg-[#7C3AED] text-white shadow-lg shadow-violet-100'
                : 'text-[#4e5968] hover:bg-[#F5F3FF] hover:text-[#7C3AED]',
            )
      }
    >
      {label}
    </NavLink>
  );
}

export function PublicLayout() {
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [designVariant, setDesignVariant] = useState(() => getPublicDesignVariant());
  const isPortalDesign = designVariant === 'portal';
  const navItems = isPortalDesign ? portalNavItems : classicNavItems;

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key === PUBLIC_DESIGN_VARIANT_STORAGE_KEY) {
        setDesignVariant(getPublicDesignVariant());
      }
    };

    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  };

  const handleDesktopNavClick = () => {
    scrollToTop();
  };

  const handleMobileNavClick = () => {
    scrollToTop();
    setMenuOpen(false);
  };

  const entry = useMemo(
    () => ({
      href: isAuthenticated ? '/app' : '/auth',
      label: isAuthenticated ? '앱으로 이동' : '무료로 시작하기',
    }),
    [isAuthenticated],
  );

  return (
    <div className={cn('min-h-screen text-slate-900', isPortalDesign ? 'bg-[#f6f7fb]' : 'bg-[#f8fafc]')}>
      <header
        className={cn(
          'sticky top-0 z-40 border-b backdrop-blur-2xl',
          isPortalDesign ? 'border-[#e5eaf2] bg-white/96' : 'border-white/70 bg-white/72',
        )}
      >
        {isPortalDesign ? (
          <div className="hidden border-b border-[#eef2f7] bg-[#f8fafc] md:block">
            <div className="mx-auto flex max-w-7xl items-center justify-end gap-4 px-4 py-2 text-xs font-bold text-[#6d7588] sm:px-6 lg:px-8">
              <Link to="/auth" onClick={handleDesktopNavClick} className="hover:text-[#1754c8]">로그인</Link>
              <Link to="/auth" onClick={handleDesktopNavClick} className="hover:text-[#1754c8]">회원가입</Link>
              <Link to="/contact" onClick={handleDesktopNavClick} className="hover:text-[#1754c8]">고객센터</Link>
              <Link to="/faq" onClick={handleDesktopNavClick} className="hover:text-[#1754c8]">이벤트</Link>
            </div>
          </div>
        ) : null}

        <div className={cn('mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8', isPortalDesign ? 'py-4' : 'py-3.5')}>
          <Link to="/" onClick={handleDesktopNavClick}>
            <UniFoliLogo size="md" subtitle={null} />
          </Link>

          <nav className={cn('hidden items-center md:flex', isPortalDesign ? 'gap-1 lg:gap-2' : 'gap-1')}>
            {navItems.map(item => (
              <PublicNavItem
                key={`${item.to}-${item.label}`}
                to={item.to}
                label={item.label}
                onClick={handleDesktopNavClick}
                variant={isPortalDesign ? 'portal' : 'classic'}
              />
            ))}
          </nav>

          <div className="hidden items-center gap-3 md:flex">
            {isPortalDesign ? (
              <Link
                to="/auth"
                onClick={handleDesktopNavClick}
                className="hidden h-11 items-center gap-2 rounded-lg border border-[#dfe5ee] bg-[#f8fafc] px-3 text-sm font-bold text-[#70798b] transition hover:border-[#ffdf55] hover:bg-white lg:flex"
              >
                <span className="rounded-md bg-[#ffdf55] px-2 py-1 text-xs font-black text-[#1f2a44]">학교/포털</span>
                <Search size={17} className="text-[#1754c8]" />
                <span>UniFoli 검색</span>
              </Link>
            ) : null}
            {location.pathname !== '/auth' ? (
              <Link
                to={entry.href}
                onClick={handleDesktopNavClick}
                className={cn(
                  buttonClassName({ variant: 'primary', size: 'md' }),
                  isPortalDesign
                    ? 'rounded-lg bg-[#1f2a44] text-white shadow-none hover:bg-[#14213d] focus-visible:ring-[#ffdf55]/40'
                    : 'bg-[#7C3AED] shadow-violet-200/70 hover:bg-[#5B21B6] focus-visible:ring-[#7C3AED]/30',
                )}
              >
                {entry.label}
                <ArrowRight size={16} />
              </Link>
            ) : null}
          </div>

          <button
            type="button"
            onClick={() => setMenuOpen(open => !open)}
            aria-label={menuOpen ? '메뉴 닫기' : '메뉴 열기'}
            className={cn(
              'inline-flex h-11 w-11 items-center justify-center border bg-white/84 backdrop-blur-md md:hidden',
              isPortalDesign
                ? 'rounded-lg border-[#dfe5ee] text-[#1754c8] shadow-sm'
                : 'rounded-2xl border-white/70 text-[#7C3AED] shadow-[0_12px_26px_rgba(124,58,237,0.12)]',
            )}
          >
            {menuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>

        {menuOpen ? (
          <div className={cn('border-t px-4 py-3 backdrop-blur-xl md:hidden', isPortalDesign ? 'border-[#e5eaf2] bg-white/96' : 'border-white/70 bg-white/86')}>
            <div className="flex flex-col gap-1">
              {navItems.map(item => (
                <PublicNavItem
                  key={`${item.to}-${item.label}`}
                  to={item.to}
                  label={item.label}
                  onClick={handleMobileNavClick}
                  variant={isPortalDesign ? 'portal' : 'classic'}
                />
              ))}
              {location.pathname !== '/auth' ? (
                <Link
                  to={entry.href}
                  onClick={handleMobileNavClick}
                  className={cn(
                    buttonClassName({ variant: 'primary', size: 'md', fullWidth: true }),
                    isPortalDesign
                      ? 'rounded-lg bg-[#1f2a44] text-white shadow-none hover:bg-[#14213d] focus-visible:ring-[#ffdf55]/40'
                      : 'bg-[#7C3AED] shadow-violet-200/70 hover:bg-[#5B21B6] focus-visible:ring-[#7C3AED]/30',
                  )}
                >
                  {entry.label}
                  <ArrowRight size={16} />
                </Link>
              ) : null}
            </div>
          </div>
        ) : null}
      </header>

      <Outlet />

      <footer className={cn('border-t backdrop-blur-xl', isPortalDesign ? 'border-[#e5eaf2] bg-white' : 'border-white/70 bg-white/72')}>
        <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[1.4fr_0.6fr] lg:px-8">
          <div className="space-y-4">
            <UniFoliLogo
              size="md"
              subtitle={isPortalDesign ? 'AI 진단 · 탐구보고서 · 면접 TALK' : '진단 · 트렌드 · 워크숍'}
            />
            <p className="max-w-2xl text-sm font-medium leading-7 text-slate-500">
              {isPortalDesign ? '학생부 기반 진로·진학 관리를 한 흐름으로 실행합니다.' : '필요한 기능만 고르면 바로 실행됩니다.'}
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/faq" onClick={handleDesktopNavClick} className={buttonClassName({ variant: 'secondary', size: 'sm' })}>
                자주 묻는 질문
              </Link>
              <Link to="/contact" onClick={handleDesktopNavClick} className={buttonClassName({ variant: 'secondary', size: 'sm' })}>
                문의하기
              </Link>
            </div>
          </div>

          <div className="space-y-4 text-sm font-medium text-slate-500 lg:text-right">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">지원</p>
              <p className="mt-2">
                <a className="font-semibold text-[#6d28d9] hover:text-[#0e7490]" href="mailto:mongben@naver.com">
                  mongben@naver.com
                </a>
              </p>
              <p className="mt-1">
                <a className="font-semibold text-[#6d28d9] hover:text-[#0e7490]" href="tel:01076142633">
                  010-7614-2633
                </a>
              </p>
            </div>
            <div className="flex flex-wrap gap-4 lg:justify-end">
              <Link to="/legal/terms" onClick={handleDesktopNavClick} className="font-semibold text-slate-600 hover:text-slate-900">
                이용약관
              </Link>
              <Link to="/legal/privacy" onClick={handleDesktopNavClick} className="font-semibold text-slate-600 hover:text-slate-900">
                개인정보처리방침
              </Link>
            </div>
            <p className="text-xs leading-6 text-slate-400">UniFoli는 준비 과정의 품질 향상을 지원하며, 입시 결과를 보장하지 않습니다.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
