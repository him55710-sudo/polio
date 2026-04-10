import React from 'react';
import { motion } from 'motion/react';
import { CheckCircle2, AlertTriangle, Zap } from 'lucide-react';
import { SectionCard, SurfaceCard } from '../primitives';
import { formatRiskLevel } from '../../lib/diagnosis';

interface DiagnosisResultDisplayProps {
  diagnosisResult: any;
}

export const DiagnosisResultDisplay: React.FC<DiagnosisResultDisplayProps> = ({ diagnosisResult }) => {
  return (
    <motion.div
      key="result"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="space-y-6"
    >
      <SectionCard
        title={diagnosisResult.headline}
        description="나의 입시 경쟁력을 요약한 AI 종합 진정 분석 리포트입니다."
        eyebrow="AI 진단 리포트"
        data-testid="diagnosis-result-panel"
        className="border-none bg-white shadow-2xl ring-1 ring-slate-200/50"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <div
              className={`flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-black shadow-lg ${
                diagnosisResult.risk_level === 'safe'
                  ? 'bg-emerald-500 text-white shadow-emerald-500/20'
                  : diagnosisResult.risk_level === 'warning'
                    ? 'bg-amber-500 text-white shadow-amber-500/20'
                    : 'bg-rose-500 text-white shadow-rose-500/20'
              }`}
            >
              {formatRiskLevel(diagnosisResult.risk_level)}
            </div>
          </div>
        }
      >
        {diagnosisResult.overview ? (
          <div className="mb-8 rounded-3xl bg-slate-50 p-6 sm:p-8">
            <p className="text-lg font-bold leading-relaxed text-slate-700">
              <span className="mb-2 block text-xs font-black uppercase tracking-widest text-slate-400">
                종합 분석 의견
              </span>
              {diagnosisResult.overview}
            </p>
          </div>
        ) : null}

        <div className="grid gap-6 md:grid-cols-2">
          <SurfaceCard className="border-none bg-emerald-50/50 p-6 ring-1 ring-emerald-100">
            <div className="mb-4 flex items-center gap-2 text-emerald-700">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-500 text-white shadow-lg shadow-emerald-500/20">
                <CheckCircle2 size={18} />
              </div>
              <span className="text-lg font-black italic">핵심 강점</span>
              <span className="text-sm font-bold opacity-60">나의 생기부 강점</span>
            </div>
            <ul className="space-y-3">
              {diagnosisResult.strengths.map((item: string, index: number) => (
                <li key={index} className="flex gap-3 text-base font-bold leading-relaxed text-slate-700">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                  {item}
                </li>
              ))}
            </ul>
          </SurfaceCard>

          <SurfaceCard className="border-none bg-rose-50/50 p-6 ring-1 ring-rose-100">
            <div className="mb-4 flex items-center gap-2 text-rose-700">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-rose-500 text-white shadow-lg shadow-rose-500/20">
                <AlertTriangle size={18} />
              </div>
              <span className="text-lg font-black italic">보완 포인트</span>
              <span className="text-sm font-bold opacity-60">보완이 필요한 부분</span>
            </div>
            <ul className="space-y-3">
              {(diagnosisResult.detailed_gaps?.length
                ? diagnosisResult.detailed_gaps.map((gap: any) => `${gap.title}: ${gap.description}`)
                : diagnosisResult.gaps
              ).map((item: string, index: number) => (
                <li key={index} className="flex gap-3 text-base font-bold leading-relaxed text-slate-700">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-rose-400" />
                  {item}
                </li>
              ))}
            </ul>
          </SurfaceCard>
        </div>

        {diagnosisResult.next_actions?.length || diagnosisResult.recommended_focus ? (
          <div className="mt-8 rounded-[2rem] bg-slate-900 p-8 text-white shadow-2xl">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/10 text-white">
                <Zap size={20} fill="currentColor" />
              </div>
              <div>
                <h4 className="text-lg font-black">실행 과제</h4>
                <p className="text-sm font-bold text-slate-400">합격을 위한 향후 액션 플랜</p>
              </div>
            </div>

            <div className="grid gap-8 lg:grid-cols-2">
              {diagnosisResult.next_actions?.length ? (
                <div className="space-y-4">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">주요 실천 과제</p>
                  <ul className="space-y-3">
                    {diagnosisResult.next_actions.map((action: string, i: number) => (
                      <li key={i} className="flex gap-3 text-base font-bold text-slate-100">
                        <span className="mt-2.5 flex h-1 w-1 shrink-0 rounded-full bg-blue-400" />
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {diagnosisResult.recommended_focus ? (
                <div className="space-y-4 border-l border-white/10 pl-8">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">추천 집중 영역</p>
                  <p className="text-lg font-bold leading-relaxed text-blue-100">
                    {diagnosisResult.recommended_focus}
                  </p>
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
      </SectionCard>
    </motion.div>
  );
};
