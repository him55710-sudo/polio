import { useCallback, useMemo, useState } from 'react';
import api from '../../../lib/api';
import type { GuidedChoiceGroup } from '../../../lib/guidedChat';
import type { WorkshopChatMessage, WorkshopMessageRole } from '../types/workshopMessages';
import type { ReviewablePatch } from '../utils/messageFormatters';

interface AddMessageInput {
  id?: string;
  role: WorkshopMessageRole;
  content: string;
  isStreaming?: boolean;
  choiceGroups?: GuidedChoiceGroup[];
}

export function useWorkshopMessages(initialMessages: WorkshopChatMessage[] = []) {
  const [messages, setMessages] = useState<WorkshopChatMessage[]>(initialMessages);

  const addMessage = useCallback((message: AddMessageInput) => {
    const next: WorkshopChatMessage = {
      id: message.id || createMessageId(message.role),
      role: message.role,
      content: message.content,
      isStreaming: message.isStreaming,
      choiceGroups: message.choiceGroups,
    };
    setMessages((prev) => [...prev, next]);
    return next;
  }, []);

  const addUserMessage = useCallback((content: string, id?: string) => addMessage({ id, role: 'user', content }), [addMessage]);
  const addAssistantMessage = useCallback((content: string, id?: string) => addMessage({ id, role: 'foli', content }), [addMessage]);
  const addStreamingMessage = useCallback(
    (id = createMessageId('foli')) => addMessage({ id, role: 'foli', content: '', isStreaming: true }),
    [addMessage],
  );

  const updateStreamingMessage = useCallback((id: string, content: string, done = false) => {
    setMessages((prev) =>
      prev.map((message) =>
        message.id === id
          ? {
              ...message,
              content,
              isStreaming: done ? false : message.isStreaming,
            }
          : message,
      ),
    );
  }, []);

  const attachPatchToMessage = useCallback((id: string, patch: ReviewablePatch) => {
    setMessages((prev) =>
      prev.map((message) =>
        message.id === id
          ? {
              ...message,
              ...(isReportPatchLike(patch) ? { reportPatch: patch } : { draftPatch: patch }),
            }
          : message,
      ),
    );
  }, []);

  const attachChoiceGroupsToMessage = useCallback((id: string, choiceGroups: GuidedChoiceGroup[]) => {
    setMessages((prev) => prev.map((message) => (message.id === id ? { ...message, choiceGroups } : message)));
  }, []);

  const toggleTopicStar = useCallback(
    async (messageId: string, topicId: string, isStarred: boolean, topicTitle: string, projectId?: string) => {
      // 1. 낙관적 UI 업데이트
      setMessages((prev) =>
        prev.map((m) => {
          if (m.id !== messageId) return m;

          const nextGroups = m.choiceGroups?.map((group) => {
            if (group.id !== 'topic-selection') return group;
            return {
              ...group,
              options: group.options.map((opt: any) =>
                opt.id === topicId ? { ...opt, is_starred: isStarred } : opt,
              ),
            };
          });

          const nextSuggestions = m.topicSuggestions?.map((s) =>
            s.id === topicId ? { ...s, is_starred: isStarred } : s,
          );

          return { ...m, choiceGroups: nextGroups, topicSuggestions: nextSuggestions };
        }),
      );

      // 2. 백엔드 연동
      try {
        await api.post('/api/v1/guided-chat/toggle-star', {
          project_id: projectId,
          topic_id: topicId,
          is_starred: isStarred,
          topic_title: topicTitle,
        });
      } catch (error) {
        console.error('Failed to toggle star:', error);
        // 실패 시 롤백 로직을 넣을 수 있지만, 여기서는 사용자 경험을 위해 생략하거나 간단히 알림만 줍니다.
      }
    },
    [],
  );

  const clearMessages = useCallback(() => setMessages([]), []);

  return useMemo(
    () => ({
      messages,
      setMessages,
      addUserMessage,
      addAssistantMessage,
      addStreamingMessage,
      updateStreamingMessage,
      attachPatchToMessage,
      attachChoiceGroupsToMessage,
      toggleTopicStar,
      clearMessages,
    }),
    [
      addAssistantMessage,
      addStreamingMessage,
      addUserMessage,
      attachChoiceGroupsToMessage,
      attachPatchToMessage,
      toggleTopicStar,
      clearMessages,
      messages,
      updateStreamingMessage,
    ],
  );
}

function createMessageId(role: WorkshopMessageRole): string {
  const random =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `${role}-${random}`;
}

function isReportPatchLike(value: ReviewablePatch): value is Extract<ReviewablePatch, { type: string }> {
  return typeof (value as { type?: unknown }).type === 'string';
}
