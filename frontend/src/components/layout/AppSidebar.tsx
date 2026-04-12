import React, { useEffect, useMemo, useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { UniFoliLogo } from '../UniFoliLogo';
import { Badge, Button } from '../ui';
import { appNavSections, isNavItemActive } from './nav-config';
import { Sidebar } from '../primitives';
import { SidebarAccountBlock } from './SidebarAccountBlock';
import { cn } from '../../lib/cn';

interface AppSidebarProps {
  pathname: string;
  isOpen: boolean;
  onToggle: () => void;
  onCloseMobile: () => void;
  userName: string;
  userPhotoUrl?: string | null;
  isGuestSession: boolean;
  onLogout: () => void;
}

const SIDEBAR_SECTION_STATE_KEY = 'unifoli_sidebar_sections_v1';

export function AppSidebar({
  pathname,
  isOpen,
  onToggle,
  onCloseMobile,
  userName,
  userPhotoUrl,
  isGuestSession,
  onLogout,
}: AppSidebarProps) {
  const activeSectionKey = useMemo(() => {
    const activeSection = appNavSections.find(section => section.items.some(item => isNavItemActive(pathname, item.path)));
    return activeSection?.key ?? appNavSections[0]?.key ?? '';
  }, [pathname]);

  const [openSections, setOpenSections] = useState<Record<string, boolean>>(() =>
    appNavSections.reduce<Record<string, boolean>>((acc, section) => {
      acc[section.key] = section.key === activeSectionKey;
      return acc;
    }, {}),
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const raw = window.localStorage.getItem(SIDEBAR_SECTION_STATE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as Record<string, boolean>;
      if (!parsed || typeof parsed !== 'object') return;
      setOpenSections(prev => ({ ...prev, ...parsed }));
    } catch {
      // Ignore invalid localStorage payload.
    }
  }, []);

  useEffect(() => {
    if (!activeSectionKey) return;
    setOpenSections(prev => {
      if (prev[activeSectionKey]) return prev;
      const next = { ...prev, [activeSectionKey]: true };
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(SIDEBAR_SECTION_STATE_KEY, JSON.stringify(next));
      }
      return next;
    });
  }, [activeSectionKey]);

  const handleSectionToggle = (sectionKey: string) => {
    setOpenSections(prev => {
      const next = { ...prev, [sectionKey]: !prev[sectionKey] };
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(SIDEBAR_SECTION_STATE_KEY, JSON.stringify(next));
      }
      return next;
    });
  };

  return (
    <Sidebar open={isOpen} aria-label="앱 주요 메뉴">
      {/* Desktop Toggle Button */}
      <div className="absolute -right-3 top-6 z-50 hidden md:block">
        <button 
          onClick={onToggle}
          className="flex h-6 w-6 items-center justify-center rounded-full border border-[#d5e3ff] bg-white shadow-[0_8px_18px_rgba(24,66,170,0.14)] transition-colors hover:bg-[#f4f8ff]"
        >
          {isOpen ? <ChevronLeft size={14} className="text-[#3056a4]" /> : <ChevronRight size={14} className="text-[#3056a4]" />}
        </button>
      </div>

      <div className={cn("flex flex-col h-full", !isOpen && "items-center")}>
        {/* Logo Section */}
        <div className={cn("mb-2 p-6", !isOpen && "px-2 py-6")}>
          <Link to="/app" onClick={onCloseMobile} className={cn('flex', !isOpen && 'justify-center')}>
            <UniFoliLogo size={isOpen ? 'md' : 'sm'} markOnly={!isOpen} subtitle={null} />
          </Link>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-2 space-y-6">
          {appNavSections.map(section => {
            const activeSection = section.items.some(item => isNavItemActive(pathname, item.path));
            const sectionOpen = !isOpen ? true : (openSections[section.key] ?? activeSection);

            return (
              <div key={section.key} className="space-y-1">
                {isOpen ? (
                  <button
                    type="button"
                    onClick={() => handleSectionToggle(section.key)}
                    className="mb-2 flex w-full items-center justify-between rounded-xl px-2 py-1.5 text-left transition-colors hover:bg-[#eef5ff]"
                    aria-expanded={sectionOpen}
                  >
                    <div>
                      <p className="text-[10px] font-black uppercase tracking-[0.2rem] text-[#6a83b1]">{section.label}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {sectionOpen ? <ChevronDown size={14} className="text-[#6a83b1]" /> : <ChevronRight size={14} className="text-[#6a83b1]" />}
                    </div>
                  </button>
                ) : (
                   <div className="mx-auto my-4 h-px w-8 bg-[#dce8ff]" />
                )}

                <div className={cn('space-y-1', !sectionOpen && isOpen && 'hidden')}>
                  {section.items.map(item => {
                    const active = isNavItemActive(pathname, item.path);
                    const Icon = item.icon;

                    return (
                      <NavLink
                        key={item.path}
                        to={item.path}
                        onClick={onCloseMobile}
                        className={cn(
                          'group flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-all duration-200',
                          active 
                            ? 'bg-[linear-gradient(135deg,#1d4fff_0%,#2da3ff_100%)] text-white shadow-[0_12px_24px_rgba(29,79,255,0.26)] font-semibold' 
                            : 'text-slate-500 hover:bg-[#eef5ff] hover:text-slate-900',
                          !isOpen && 'justify-center px-0 h-10 w-10 mx-auto',
                        )}
                      >
                        <Icon size={18} className={cn(active ? 'text-white' : 'text-slate-400 group-hover:text-[#3559a8]')} />
                        {isOpen && (
                          <div className="min-w-0 flex-1">
                            <p className="truncate">{item.label}</p>
                          </div>
                        )}
                      </NavLink>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </nav>

        <div className="mt-auto border-t border-[#dce8ff] p-4">
          <SidebarAccountBlock
            userName={userName}
            userPhotoUrl={userPhotoUrl}
            isGuestSession={isGuestSession}
            isExpanded={isOpen}
            onLogout={onLogout}
          />
        </div>
      </div>
    </Sidebar>
  );
}
