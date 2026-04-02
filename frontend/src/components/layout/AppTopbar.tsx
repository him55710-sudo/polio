import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Flag, Menu, X } from 'lucide-react';
import { UniFoliaLogo } from '../UniFoliaLogo';
import { Button } from '../ui';
import { Topbar } from '../primitives';
import { WorkflowContextHeader } from './WorkflowContextHeader';
import { resolveApiBaseUrl } from '../../lib/api';

interface AppTopbarProps {
  currentSectionLabel: string;
  summary: string;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  primaryGoal?: {
    university: string;
    major?: string;
  } | null;
}

const API_BASE_URL = resolveApiBaseUrl();

export function AppTopbar({ currentSectionLabel, summary, isSidebarOpen, onToggleSidebar, primaryGoal }: AppTopbarProps) {
  return (
    <>
      <Topbar mobile>
        <Link to="/app">
          <UniFoliaLogo size="sm" subtitle={null} />
        </Link>
        <Button variant="ghost" size="icon" aria-label={isSidebarOpen ? '사이드바 닫기' : '사이드바 열기'} onClick={onToggleSidebar}>
          {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </Button>
      </Topbar>

      {primaryGoal ? (
        <div className="border-b border-slate-200 bg-blue-50 px-4 py-2 md:hidden">
          <div className="flex items-center gap-2">
            <img
              src={`${API_BASE_URL}/api/v1/assets/univ-logo?name=${encodeURIComponent(primaryGoal.university)}`}
              className="h-7 w-7 rounded-md bg-white object-contain p-1"
              alt={`${primaryGoal.university} 로고`}
              onError={event => {
                event.currentTarget.style.display = 'none';
              }}
            />
            <p className="truncate text-sm font-black text-slate-800">
              목표: {primaryGoal.university}
              {primaryGoal.major ? ` · ${primaryGoal.major}` : ''}
            </p>
          </div>
        </div>
      ) : null}

      <Topbar>
        <WorkflowContextHeader sectionLabel={currentSectionLabel} summary={summary} />

        <div className="flex items-center gap-3">
          {primaryGoal ? (
            <div className="hidden items-center gap-2 rounded-2xl border border-blue-200 bg-blue-50 px-3 py-2 lg:flex">
              <img
                src={`${API_BASE_URL}/api/v1/assets/univ-logo?name=${encodeURIComponent(primaryGoal.university)}`}
                className="h-8 w-8 rounded-lg bg-white object-contain p-1"
                alt={`${primaryGoal.university} 로고`}
                onError={event => {
                  event.currentTarget.style.display = 'none';
                }}
              />
              <div className="min-w-0">
                <p className="text-[11px] font-black uppercase tracking-[0.14em] text-blue-600">Dream School</p>
                <p className="max-w-[220px] truncate text-sm font-black text-slate-800">
                  {primaryGoal.university}
                  {primaryGoal.major ? ` · ${primaryGoal.major}` : ''}
                </p>
              </div>
              <Flag size={14} className="text-blue-600" />
            </div>
          ) : null}

          <Link
            to="/"
            className="inline-flex items-center gap-2 rounded-2xl border border-slate-300 bg-white px-3 py-2 text-sm font-bold text-slate-600 hover:bg-slate-50"
          >
            <ArrowLeft size={14} />
            공개 사이트
          </Link>
        </div>
      </Topbar>
    </>
  );
}
