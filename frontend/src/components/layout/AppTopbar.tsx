import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Menu, X } from 'lucide-react';
import { UniFoliLogo } from '../UniFoliLogo';
import { UniversityLogo } from '../UniversityLogo';
import { Button } from '../ui';
import { Topbar } from '../primitives';
import { WorkflowContextHeader } from './WorkflowContextHeader';
import { cn } from '../../lib/cn';

interface GoalItem {
  university: string;
  major?: string;
}

interface AppTopbarProps {
  currentSectionLabel: string;
  summary: string;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  primaryGoal?: GoalItem | null;
  rankedGoals?: GoalItem[];
}

const goalToneClasses = [
  {
    shell: 'border-indigo-200/50 bg-indigo-50/80 text-indigo-700 shadow-lg shadow-indigo-100/50',
    rank: 'text-indigo-600',
    logo: 'bg-white',
  },
  {
    shell: 'border-purple-200/50 bg-purple-50/80 text-purple-700 shadow-lg shadow-purple-100/50',
    rank: 'text-purple-600',
    logo: 'bg-white',
  },
  {
    shell: 'border-pink-200/50 bg-pink-50/80 text-pink-700 shadow-lg shadow-pink-100/50',
    rank: 'text-pink-600',
    logo: 'bg-white',
  },
];

export function AppTopbar({
  currentSectionLabel,
  summary,
  isSidebarOpen,
  onToggleSidebar,
  primaryGoal,
  rankedGoals,
}: AppTopbarProps) {
  const visibleGoals = (rankedGoals?.length ? rankedGoals : primaryGoal ? [primaryGoal] : []).slice(0, 6);

  return (
    <>
      <Topbar mobile>
        <Link to="/app">
          <UniFoliLogo size="sm" subtitle={null} />
        </Link>
        <Button variant="ghost" size="icon" aria-label={isSidebarOpen ? '사이드바 닫기' : '사이드바 열기'} onClick={onToggleSidebar}>
          {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </Button>
      </Topbar>

      {visibleGoals.length ? (
        <div className="border-b border-white/70 bg-[linear-gradient(180deg,rgba(248,250,255,0.84)_0%,rgba(241,246,255,0.8)_100%)] px-3 py-2.5 md:hidden">
          <div className="flex gap-2.5 overflow-x-auto pb-0.5">
            {visibleGoals.map((goal, index) => {
              const tone = goalToneClasses[index % goalToneClasses.length];

              return (
                <div
                  key={`${goal.university}-${goal.major ?? ''}-${index}`}
                  className={cn('flex min-w-[156px] items-center gap-2.5 rounded-2xl border px-3 py-2 sm:min-w-[176px]', tone.shell)}
                >
                  <UniversityLogo
                    universityName={goal.university}
                    className={cn('h-8 w-8 rounded-xl object-contain p-1.5', tone.logo)}
                    fallbackClassName="border border-[#d6e4ff]"
                  />
                  <div className="min-w-0">
                    <p className={cn('truncate text-[11px] font-black', tone.rank)}>{index + 1}순위</p>
                    <p className="truncate text-xs font-black text-slate-900">{goal.university}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      <Topbar>
        <WorkflowContextHeader sectionLabel={currentSectionLabel} summary={summary} />

        <div className="flex items-center gap-3">
          {visibleGoals.length ? (
            <div className="hidden max-w-[620px] items-center gap-2.5 overflow-x-auto rounded-[1.6rem] border border-white/70 bg-white/68 px-3.5 py-2.5 shadow-[0_14px_30px_rgba(42,64,132,0.08)] backdrop-blur-xl lg:flex">
              {visibleGoals.map((goal, index) => {
                const tone = goalToneClasses[index % goalToneClasses.length];

                return (
                  <div
                    key={`${goal.university}-${goal.major ?? ''}-${index}`}
                    className={cn('flex min-w-[186px] items-center gap-2.5 rounded-2xl border px-3 py-2', tone.shell)}
                  >
                    <UniversityLogo
                      universityName={goal.university}
                      className={cn('h-8 w-8 rounded-xl object-contain p-1.5', tone.logo)}
                      fallbackClassName="border border-[#d6e4ff]"
                    />
                    <div className="min-w-0">
                      <p className={cn('truncate text-[11px] font-black', tone.rank)}>{index + 1}순위</p>
                      <p className="truncate text-xs font-black text-slate-900">{goal.university}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : null}

          <Link
            to="/"
            className="inline-flex items-center gap-2 rounded-2xl border border-white/70 bg-white/84 px-3.5 py-2.5 text-sm font-bold text-[#35518d] shadow-[0_12px_26px_rgba(42,64,132,0.08)] backdrop-blur-md transition-colors hover:bg-[#f7f9ff]"
          >
            <ArrowLeft size={14} />
            공개 페이지
          </Link>
        </div>
      </Topbar>
    </>
  );
}
