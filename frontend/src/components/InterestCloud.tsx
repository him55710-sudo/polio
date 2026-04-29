import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { Star, Sparkles } from 'lucide-react';
import { api } from '../lib/api';
import { SectionCard } from './primitives';

interface InterestCloudProps {
  className?: string;
}

export const InterestCloud: React.FC<InterestCloudProps> = ({ className }) => {
  const [keywords, setKeywords] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get<{ starred_keywords: string[] }>('/api/v1/users/me/interests')
      .then(res => {
        setKeywords(res.starred_keywords || []);
      })
      .catch(err => {
        console.error('Failed to fetch interests:', err);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  if (!isLoading && keywords.length === 0) return null;

  return (
    <SectionCard
      title="나의 관심 키워드"
      subtitle="워크숍에서 별표로 저장한 관심사들입니다."
      className={className}
      badge="Interest Library"
    >
      {isLoading ? (
        <div className="flex h-32 items-center justify-center">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
        </div>
      ) : (
        <div className="flex flex-wrap gap-2 py-2">
          {keywords.map((keyword, index) => (
            <motion.div
              key={`${keyword}-${index}`}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.05 }}
              className="group relative flex items-center gap-1.5 rounded-2xl border border-indigo-100 bg-white px-4 py-2 text-sm font-black text-indigo-600 shadow-sm transition-all hover:border-indigo-600 hover:bg-indigo-50"
            >
              <Star size={14} fill="currentColor" className="text-indigo-400 group-hover:text-indigo-600" />
              <span>{keyword}</span>
              <div className="absolute -right-1 -top-1 hidden group-hover:block">
                <Sparkles size={10} className="animate-pulse text-indigo-600" />
              </div>
            </motion.div>
          ))}
          
          <div className="mt-4 flex w-full items-center gap-2 rounded-xl bg-slate-50 p-3 text-[13px] font-medium text-slate-500">
            <Sparkles size={14} className="text-indigo-400" />
            <span>이 키워드들은 탐구 주제 추천 시 AI가 적극적으로 반영합니다.</span>
          </div>
        </div>
      )}
    </SectionCard>
  );
};
