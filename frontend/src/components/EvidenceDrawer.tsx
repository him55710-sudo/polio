import React, { useState } from 'react';
import { ShieldCheck, ChevronDown, ChevronUp, Link as LinkIcon, AlertCircle } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';

interface EvidenceDrawerProps {
  evidenceMap: Record<string, any> | null;
}

export function EvidenceDrawer({ evidenceMap }: EvidenceDrawerProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!evidenceMap || Object.keys(evidenceMap).length === 0) return null;

  return (
    <div className="mx-auto max-w-[210mm] mt-6 overflow-hidden rounded-2xl border border-[#004aad]/20 bg-white shadow-lg clay-card">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="group flex w-full items-center justify-between bg-[#004aad]/5 px-6 py-4 transition-colors hover:bg-[#004aad]/10"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#004aad]/10 text-[#004aad] shadow-sm transition-transform group-hover:scale-110">
            <ShieldCheck size={20} />
          </div>
          <div className="text-left">
            <h4 className="text-sm font-extrabold text-[#004aad] tracking-tight">AI 작성 텍스트의 출처 증빙 다이어그램</h4>
            <p className="mt-0.5 text-xs font-semibold text-[#004aad]/60">위 문서 내용이 어느 맥락에서 도출되었는지 투명하게 공개합니다.</p>
          </div>
        </div>
        <div className="rounded-full bg-[#004aad]/10 p-1.5 text-[#004aad] transition-colors group-hover:bg-[#004aad]/20">
          {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="border-t border-emerald-100/50"
          >
            <div className="p-6 space-y-4 bg-[#004aad]/5">
              <div className="mb-4 flex items-start gap-2 rounded-xl bg-white p-4 border border-[#004aad]/10">
                <AlertCircle size={16} className="mt-0.5 text-[#004aad] shrink-0" />
                <p className="text-xs font-semibold text-[#004aad] leading-relaxed">
                  UniFoli는 학생이 제출한 대화 및 근거 맥락 내에서만 텍스트를 생성하며, 존재하지 않는 허위 사실이나 수치는 배제합니다. 
                  아래 카드는 AI가 요약 생성한 각 주장이 어떤 원본 근거에서 도출되었는지 매핑해줍니다.
                </p>
              </div>

              {Object.entries(evidenceMap).map(([claim, data], i) => (
                <div key={i} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
                  <div className="mb-4 flex items-start flex-col sm:flex-row gap-3">
                    <span className="shrink-0 rounded-lg bg-slate-100 px-2.5 py-1 text-[10px] font-black uppercase text-slate-500 border border-slate-200">AI 주장 요약</span>
                    <p className="text-[15px] font-bold text-slate-700 leading-snug">{claim}</p>
                  </div>
                  
                  <div className="ml-2 pl-4 sm:ml-[86px] sm:pl-4 border-l-2 border-slate-100">
                     <div className="mb-3 flex flex-col items-start gap-2">
                       <span className="shrink-0 rounded-md bg-[#004aad]/10 px-2 py-0.5 text-[10px] font-black uppercase tracking-wider text-[#004aad]">추출된 원본 텍스트의 근거</span>
                       <p className="text-sm font-medium text-slate-600 leading-relaxed break-keep">
                         {typeof data === 'object' && data.근거 ? data.근거 : JSON.stringify(data)}
                       </p>
                     </div>
                     <div className="flex items-center gap-1.5 mt-4 border-t border-slate-50 pt-3">
                       <LinkIcon size={12} className="text-slate-400" />
                       <span className="text-[10px] font-bold text-slate-400 font-mono tracking-widest uppercase">
                         Source: {typeof data === 'object' && data.출처 ? String(data.출처) : 'unknown'}
                       </span>
                     </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
