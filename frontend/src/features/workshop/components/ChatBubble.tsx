import React, { memo, useMemo } from 'react';
import { Bot, Loader2, User } from 'lucide-react';
import { motion } from 'motion/react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import type { GuidedChoiceGroup, GuidedChoiceOption } from '../../../lib/guidedChat';
import type { WorkshopDraftPatchProposal } from '../../../lib/workshopCoauthoring';
import { cn } from '../../../lib/cn';
import type { ReportPatch } from '../types/reportDocument';
import type { WorkshopChatMessage } from '../types/workshopMessages';
import { buildTopicChoiceGroupFromSuggestions } from '../utils/guidedChoiceHelpers';
import { ChoiceCardGroup } from './ChoiceCardGroup';
import { PatchReviewCard } from './PatchReviewCard';
import { ResearchCandidateCard } from './ResearchCandidateCard';
import { useWorkshopStar } from '../hooks/useWorkshopStar';

type ReviewPatch = ReportPatch | WorkshopDraftPatchProposal;

interface ChatBubbleProps {
  message: WorkshopChatMessage;
  onGuidedChoiceSelect: (groupId: string, option: GuidedChoiceOption, message: WorkshopChatMessage) => void | Promise<void>;
  onApplyPatch: (patch: ReviewPatch, message: WorkshopChatMessage) => void | Promise<void>;
  onRejectPatch: (patch: ReviewPatch, message: WorkshopChatMessage) => void | Promise<void>;
  onRequestPatchRewrite?: (
    patch: ReviewPatch,
    tone: 'simpler' | 'professional' | 'custom',
    message: WorkshopChatMessage,
  ) => void | Promise<void>;
  onUseResearchCandidate?: (candidateId: string, message: WorkshopChatMessage) => void | Promise<void>;
  onRefineResearchCandidate?: (candidateId: string, message: WorkshopChatMessage) => void | Promise<void>;
  onExcludeResearchCandidate?: (candidateId: string, message: WorkshopChatMessage) => void | Promise<void>;
  onStarToggle?: (topicId: string, isStarred: boolean, label: string) => void | Promise<void>;
  isGuidedActionLoading?: boolean;
  selectingTopicId?: string | null;
}

const MarkdownContent = memo(function MarkdownContent({
  content,
  isUserMessage,
}: {
  content: string;
  isUserMessage: boolean;
}) {
  return (
    <div
      className={cn(
        'prose prose-slate max-w-none text-sm leading-relaxed',
        isUserMessage ? 'prose-invert text-white' : 'text-slate-900',
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          h3: ({ children, ...props }) => (
            <h3
              {...props}
              className={cn('mb-3 mt-6 text-lg font-black', isUserMessage ? 'text-white' : 'text-slate-900')}
            >
              {children}
            </h3>
          ),
          p: ({ children, ...props }) => (
            <p
              {...props}
              className={cn('text-[15px] font-medium leading-7', isUserMessage ? 'whitespace-pre-wrap text-white' : 'text-slate-800')}
            >
              {children}
            </p>
          ),
          ul: ({ children, ...props }) => (
            <ul {...props} className={cn('mb-4 ml-4 list-disc space-y-2', isUserMessage ? 'text-white/90' : 'text-slate-700')}>
              {children}
            </ul>
          ),
          ol: ({ children, ...props }) => (
            <ol {...props} className={cn('mb-4 ml-4 list-decimal space-y-2', isUserMessage ? 'text-white/90' : 'text-slate-700')}>
              {children}
            </ol>
          ),
          li: ({ children, ...props }) => <li {...props} className="text-sm leading-relaxed">{children}</li>,
          code: ({ className, children, ...props }) => {
            const isInline = !/language-(\w+)/.test(className || '');
            return isInline ? (
              <code {...props} className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs font-bold text-indigo-600">
                {children}
              </code>
            ) : (
              <pre className="mt-2 overflow-x-auto rounded-xl bg-slate-900 p-4">
                <code {...props} className={cn('font-mono text-xs text-slate-200', className)}>
                  {children}
                </code>
              </pre>
            );
          },
          strong: ({ children }) => (
            <strong className={cn('font-extrabold', isUserMessage ? 'text-white' : 'text-indigo-600')}>{children}</strong>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});

export const ChatBubble = memo(function ChatBubble({
  message,
  onGuidedChoiceSelect,
  onApplyPatch,
  onRejectPatch,
  onRequestPatchRewrite,
  onUseResearchCandidate,
  onRefineResearchCandidate,
  onExcludeResearchCandidate,
  onStarToggle: _onStarToggleProp, // 부모의 prop은 무시 (훅 사용)
  isGuidedActionLoading,
  selectingTopicId,
}: ChatBubbleProps) {
  const isUser = message.role === 'user';
  const isStreaming = Boolean(message.isStreaming || (message as unknown as Record<string, unknown>).isStreaming);
  const reviewPatch = message.reportPatch || message.draftPatch || null;
  
  // 훅을 사용하여 직접 서버 동기화 처리 (Workshop.tsx 수정 최소화)
  const { toggleTopicStar } = useWorkshopStar();

  const interactiveGroups = useMemo<GuidedChoiceGroup[]>(() => {
    if (message.choiceGroups?.length) return message.choiceGroups;
    if (message.phase === 'topic_selection' && message.topicSuggestions?.length) {
      return [buildTopicChoiceGroupFromSuggestions(message.topicSuggestions)];
    }
    return [];
  }, [message.choiceGroups, message.phase, message.topicSuggestions]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn('flex w-full px-2', isUser ? 'justify-end' : 'justify-start')}
    >
      <div
        className={cn(
          'max-w-[92%] rounded-2xl border px-4 py-3 shadow-sm',
          isUser
            ? 'border-indigo-600 bg-indigo-600 text-white shadow-indigo-200/40'
            : 'border-slate-100 bg-white text-slate-900',
        )}
      >
        <div className={cn('mb-2 flex items-center gap-2 text-[11px] font-black uppercase tracking-wider', isUser ? 'text-indigo-100' : 'text-indigo-600')}>
          {isUser ? <User size={12} /> : <Bot size={12} />}
          <span>{isUser ? 'ME' : 'UNIFOLI'}</span>
        </div>

        {isStreaming ? (
          <div className="flex items-center gap-2 py-1 text-sm font-medium">
            <Loader2 size={14} className="animate-spin" />
            <span>분석하고 있어요...</span>
          </div>
        ) : message.content ? (
          <MarkdownContent content={message.content} isUserMessage={isUser} />
        ) : null}

        {!isUser && reviewPatch ? (
          <PatchReviewCard
            className="mt-4"
            patch={reviewPatch}
            sources={message.researchSources}
            validation={message.patchValidation}
            onApply={(patch) => void onApplyPatch(patch, message)}
            onReject={(patch) => void onRejectPatch(patch, message)}
            onRequestRewrite={(patch, tone) => void onRequestPatchRewrite?.(patch, tone, message)}
          />
        ) : null}

        {!isUser && message.researchCandidates?.length ? (
          <div className="mt-4 space-y-3">
            {message.researchCandidates.map((candidate) => (
              <ResearchCandidateCard
                key={candidate.id}
                candidate={candidate}
                sources={message.researchSources}
                onUse={() => void onUseResearchCandidate?.(candidate.id, message)}
                onRefine={() => void onRefineResearchCandidate?.(candidate.id, message)}
                onExclude={() => void onExcludeResearchCandidate?.(candidate.id, message)}
              />
            ))}
          </div>
        ) : null}

        {!isUser && interactiveGroups.length > 0 ? (
          <div className="mt-4 space-y-3">
            {interactiveGroups.map((group) => (
              <ChoiceCardGroup
                key={group.id}
                group={group}
                isGuidedActionLoading={isGuidedActionLoading}
                selectingTopicId={selectingTopicId}
                onSelect={(groupId, option) => void onGuidedChoiceSelect(groupId, option, message)}
                onStarToggle={toggleTopicStar}
              />
            ))}
          </div>
        ) : null}
      </div>
    </motion.div>
  );
});
