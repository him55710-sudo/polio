import React from 'react';
import { LogOut } from 'lucide-react';
import { Badge } from '../ui';
import { cn } from '../../lib/cn';

interface SidebarAccountBlockProps {
  userName: string;
  userPhotoUrl?: string | null;
  isGuestSession: boolean;
  isExpanded: boolean;
  onLogout: () => void;
}

export function SidebarAccountBlock({
  userName,
  userPhotoUrl,
  isGuestSession,
  isExpanded,
  onLogout,
}: SidebarAccountBlockProps) {
  return (
    <div className={cn('rounded-2xl border border-slate-200 bg-white p-3', !isExpanded && 'flex justify-center p-2')}>
      <div className="flex items-center gap-3">
        {userPhotoUrl ? (
          <img src={userPhotoUrl} alt="프로필 이미지" className="h-9 w-9 rounded-full border border-slate-200 object-cover" />
        ) : (
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-100 text-sm font-black text-blue-700">
            {(userName || '').trim().slice(0, 1).toUpperCase()}
          </div>
        )}

        {isExpanded ? (
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold text-slate-800">{userName || '사용자'}</p>
            <div className="mt-1 flex items-center gap-2">
              {isGuestSession ? <Badge tone="warning">게스트</Badge> : null}
              <button
                type="button"
                onClick={onLogout}
                className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-red-600"
              >
                <LogOut size={12} />
                로그아웃
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
