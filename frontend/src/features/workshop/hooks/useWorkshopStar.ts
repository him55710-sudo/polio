import { useCallback } from 'react';
import { useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { api } from '../../../lib/api';

export function useWorkshopStar() {
  const { projectId } = useParams<{ projectId: string }>();

  const toggleTopicStar = useCallback(
    async (topicId: string, isStarred: boolean, label: string) => {
      if (!projectId || projectId === 'demo') {
        console.warn('Demo mode or missing projectId: star status will not be persisted.');
        return;
      }

      try {
        await api.post('/api/v1/guided-chat/toggle-star', {
          project_id: projectId,
          topic_id: topicId,
          is_starred: isStarred,
          topic_title: label,
        });
      } catch (error) {
        console.error('Failed to toggle topic star:', error);
        toast.error('별표 설정을 저장하지 못했습니다.');
        throw error;
      }
    },
    [projectId],
  );

  return { toggleTopicStar, projectId };
}
