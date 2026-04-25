import React from 'react';
import { CheckCircle2, Loader2 } from 'lucide-react';
import type { GuidedChoiceGroup, GuidedChoiceOption } from '../../../lib/guidedChat';
import { cn } from '../../../lib/cn';
import { getChoiceValue, isChoiceBusy, isChoiceDisabled } from '../utils/guidedChoiceHelpers';

export interface ChoiceCardOption {
  id: string;
  label: string;
  description?: string;
  value?: unknown;
}

interface ChoiceCardGroupProps {
  group?: GuidedChoiceGroup;
  groupId?: string;
  title?: string;
  style?: 'cards' | 'chips' | 'buttons';
  options?: GuidedChoiceOption[];
  selectedId?: string | null;
  isGuidedActionLoading?: boolean;
  selectingTopicId?: string | null;
  disabled?: boolean;
  onSelect: (groupId: string, option: GuidedChoiceOption) => void;
}

export function ChoiceCardGroup({
  group,
  groupId,
  title,
  style,
  options,
  selectedId,
  isGuidedActionLoading = false,
  selectingTopicId,
  disabled = false,
  onSelect,
}: ChoiceCardGroupProps) {
  const resolvedGroupId = group?.id || groupId || 'choice-group';
  const resolvedTitle = group?.title || title || '선택하세요.';
  const resolvedStyle = group?.style || style || 'cards';
  const resolvedOptions = group?.options || options || [];

  if (!resolvedOptions.length) {
    return null;
  }

  return (
    <section className="rounded-xl border border-slate-100 bg-slate-50/70 p-3">
      <p className="mb-2 text-[11px] font-black uppercase tracking-wide text-indigo-600/75">{resolvedTitle}</p>
      <div
        className={cn(
          resolvedStyle === 'chips' ? 'flex flex-wrap gap-2' : 'grid gap-2',
          resolvedStyle === 'buttons' && 'sm:grid-cols-2',
        )}
      >
        {resolvedOptions.map((option) => {
          const optionValue = getChoiceValue(option);
          const busy = isChoiceBusy(resolvedGroupId, option, selectingTopicId);
          const optionDisabled = disabled || isChoiceDisabled(resolvedGroupId, option, isGuidedActionLoading, selectingTopicId);
          const selected = selectedId === option.id || selectedId === optionValue;

          if (resolvedStyle === 'chips') {
            return (
              <button
                key={`${resolvedGroupId}:${option.id}`}
                type="button"
                onClick={() => onSelect(resolvedGroupId, option)}
                disabled={optionDisabled}
                className={cn(
                  'inline-flex min-h-9 items-center justify-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-bold transition-colors',
                  selected
                    ? 'border-indigo-400 bg-indigo-50 text-indigo-700'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-indigo-300 hover:text-indigo-600',
                  optionDisabled && 'cursor-not-allowed opacity-60',
                )}
              >
                {busy ? <Loader2 size={13} className="animate-spin" /> : null}
                {option.label}
              </button>
            );
          }

          return (
            <button
              key={`${resolvedGroupId}:${option.id}`}
              type="button"
              onClick={() => onSelect(resolvedGroupId, option)}
              disabled={optionDisabled}
              className={cn(
                'w-full rounded-xl border bg-white p-3 text-left transition-all',
                selected
                  ? 'border-indigo-400 bg-indigo-50 shadow-sm'
                  : 'border-slate-100 hover:border-indigo-300 hover:shadow-sm',
                optionDisabled && 'cursor-not-allowed opacity-60',
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-black text-slate-900">{option.label}</p>
                  {option.description ? (
                    <p className="mt-1 text-xs font-medium leading-5 text-slate-600">{option.description}</p>
                  ) : null}
                </div>
                <div className="mt-0.5 shrink-0 text-indigo-600">
                  {busy ? <Loader2 size={16} className="animate-spin" /> : selected ? <CheckCircle2 size={16} /> : null}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
