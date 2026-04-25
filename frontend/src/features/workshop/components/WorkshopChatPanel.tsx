import React from 'react';
import { Loader2, Send } from 'lucide-react';
import type { GuidedChoiceOption } from '../../../lib/guidedChat';
import { cn } from '../../../lib/cn';
import type { WorkshopChatMessage } from '../types/workshopMessages';
import type { ReviewablePatch } from '../utils/messageFormatters';
import { ChatBubble } from './ChatBubble';

interface WorkshopChatPanelProps {
  messages?: WorkshopChatMessage[];
  input?: string;
  setInput?: (value: string) => void;
  isTyping?: boolean;
  isLoading?: boolean;
  placeholder?: string;
  header?: React.ReactNode;
  footer?: React.ReactNode;
  messagesEndRef?: React.RefObject<HTMLDivElement | null>;
  isGuidedActionLoading?: boolean;
  selectingTopicId?: string | null;
  onSubmit?: () => void | Promise<void>;
  onGuidedChoiceSelect?: (groupId: string, option: GuidedChoiceOption, message: WorkshopChatMessage) => void | Promise<void>;
  onApplyPatch?: (patch: ReviewablePatch, message: WorkshopChatMessage) => void | Promise<void>;
  onRejectPatch?: (patch: ReviewablePatch, message: WorkshopChatMessage) => void | Promise<void>;
  onRequestPatchRewrite?: (
    patch: ReviewablePatch,
    tone: 'simpler' | 'professional' | 'custom',
    message: WorkshopChatMessage,
  ) => void | Promise<void>;
  onUseResearchCandidate?: (candidateId: string, message: WorkshopChatMessage) => void | Promise<void>;
  onRefineResearchCandidate?: (candidateId: string, message: WorkshopChatMessage) => void | Promise<void>;
  onExcludeResearchCandidate?: (candidateId: string, message: WorkshopChatMessage) => void | Promise<void>;
  onStarToggle?: (messageId: string, topicId: string) => void | Promise<void>;
  children?: React.ReactNode;
  className?: string;
}

export function WorkshopChatPanel({
  messages,
  input = '',
  setInput,
  isTyping = false,
  isLoading = false,
  placeholder = 'AI와 함께 보고서를 다듬어 보세요.',
  header,
  footer,
  messagesEndRef,
  isGuidedActionLoading,
  selectingTopicId,
  onSubmit,
  onGuidedChoiceSelect,
  onApplyPatch,
  onRejectPatch,
  onRequestPatchRewrite,
  onUseResearchCandidate,
  onRefineResearchCandidate,
  onExcludeResearchCandidate,
  children,
  className,
}: WorkshopChatPanelProps) {
  if (!messages) {
    return <section className={cn('flex min-h-0 flex-col overflow-hidden bg-white', className)}>{children}</section>;
  }

  return (
    <section className={cn('flex h-full min-h-0 flex-col overflow-hidden bg-white', className)}>
      {header}
      <div className="flex-1 space-y-6 overflow-y-auto px-4 py-4 scroll-smooth">
        {isLoading ? (
          <div className="flex h-full items-center justify-center py-20">
            <Loader2 size={24} className="animate-spin text-blue-600" />
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <ChatBubble
                key={message.id}
                message={message}
                onGuidedChoiceSelect={(groupId, option, sourceMessage) => onGuidedChoiceSelect?.(groupId, option, sourceMessage)}
                onApplyPatch={(patch, sourceMessage) => onApplyPatch?.(patch, sourceMessage)}
                onRejectPatch={(patch, sourceMessage) => onRejectPatch?.(patch, sourceMessage)}
                onRequestPatchRewrite={(patch, tone, sourceMessage) => onRequestPatchRewrite?.(patch, tone, sourceMessage)}
                onUseResearchCandidate={(candidateId, sourceMessage) => onUseResearchCandidate?.(candidateId, sourceMessage)}
                onRefineResearchCandidate={(candidateId, sourceMessage) => onRefineResearchCandidate?.(candidateId, sourceMessage)}
                onExcludeResearchCandidate={(candidateId, sourceMessage) => onExcludeResearchCandidate?.(candidateId, sourceMessage)}
                onStarToggle={(topicId) => onStarToggle?.(message.id, topicId)}
                isGuidedActionLoading={isGuidedActionLoading}
                selectingTopicId={selectingTopicId}
              />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>
      {footer ?? (
        <div className="border-t border-slate-100 bg-white p-4">
          <div className="flex items-center gap-3">
            <input
              value={input}
              onChange={(event) => setInput?.(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  void onSubmit?.();
                }
              }}
              placeholder={placeholder}
              disabled={isTyping || isGuidedActionLoading}
              className="h-12 flex-1 rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 text-[15px] font-medium text-slate-900 outline-none transition-all placeholder:text-slate-400 focus:border-blue-400 focus:bg-white disabled:opacity-50"
            />
            <button
              type="button"
              onClick={() => void onSubmit?.()}
              disabled={!input.trim() || isTyping || isGuidedActionLoading}
              className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#3182f6] text-white shadow-lg shadow-blue-100 transition-all hover:bg-[#1b64da] disabled:bg-slate-200"
            >
              {isTyping ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
