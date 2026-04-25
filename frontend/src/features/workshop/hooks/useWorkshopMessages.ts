import { useCallback, useMemo, useState } from 'react';
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
      clearMessages,
    }),
    [
      addAssistantMessage,
      addStreamingMessage,
      addUserMessage,
      attachChoiceGroupsToMessage,
      attachPatchToMessage,
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
