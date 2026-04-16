import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import {
  ArrowRight,
  Compass,
  FileSearch,
  Rocket,
  ShieldCheck,
  Sparkles,
  Target,
} from 'lucide-react';
import { buttonClassName } from '../components/ui';
import { useAuth } from '../contexts/AuthContext';
import { cn } from '../lib/cn';

const workflowPanels = [
  {
    eyebrow: 'Targets',
    title: '목표 대학과 학과 기준 맞추기',
    description: '대학과 학과에 따라 같은 학생부라도 읽는 기준이 달라집니다.',
    icon: Target,
    tone: 'sky',
  },
  {
    eyebrow: 'Evidence',
    title: '학생부 PDF에서 근거만 추출하기',
    description: '텍스트를 먼저 정리한 뒤 실제 기록이 남아 있는 문장만 증거로 씁니다.',
    icon: FileSearch,
    tone: 'violet',
  },
  {
    eyebrow: 'Direction',
    title: '약점과 다음 행동까지 바로 연결하기',
    description: '진단이 끝나면 바로 워크숍으로 이어서 초안과 활동 방향을 잡을 수 있습니다.',
    icon: Compass,
    tone: 'emerald',
  },
];

const principles = [
  {
    title: '많이 읽게 하지 않습니다',
    description: '첫 화면에서는 지금 해야 할 행동 하나만 크게 보여줍니다.',
  },
  {
    title: '좋아 보이는 말보다 기록을 먼저 봅니다',
    description: '학생부 원문에 없는 강한 주장은 만들지 않고, 근거가 약하면 먼저 경고합니다.',
  },
  {
    title: '진단을 문서 작업과 분리하지 않습니다',
    description: '진단 결과, 보고서, 챗봇 질문이 같은 아티팩트를 공유하도록 설계했습니다.',
  },
];

const trustRows = [
  '학생부에 없는 내용은 추천하지 않습니다.',
  '애매한 문장은 먼저 경고합니다.',
  '진단 뒤에는 바로 워크숍으로 이어집니다.',
];

export function Landing() {
  const { isAuthenticated } = useAuth();
  const startHref = isAuthenticated ? '/app/diagnosis' : '/auth';

  const scrollToTop = () => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  };

  return (
    <div className="bg-[#f8fafc] text-slate-900 selection:bg-indigo-100">
      <section className="relative overflow-hidden py-16 lg:py-24">
        {/* Dynamic Background Elements */}
        <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_20%_20%,rgba(99,102,241,0.1),transparent_40%),radial-gradient(circle_at_80%_80%,rgba(168,85,247,0.1),transparent_40%)]" />
        <div className="pointer-events-none absolute top-[-10%] left-[10%] h-[500px] w-[500px] rounded-full bg-indigo-500/5 blur-[120px] animate-pulse-soft" />
        <div className="pointer-events-none absolute bottom-[-10%] right-[10%] h-[500px] w-[500px] rounded-full bg-purple-500/5 blur-[120px] animate-pulse-soft" />

        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid items-center gap-16 lg:grid-cols-[1fr_1.1fr]">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
              className="max-w-2xl text-center lg:text-left"
            >
              <div className="inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-white/60 px-4 py-2 text-[12px] font-bold uppercase tracking-[0.2em] text-indigo-600 backdrop-blur-sm shadow-sm animate-rise-in">
                <Sparkles size={14} className="animate-pulse" />
                <span>Next-Gen Diagnosis</span>
              </div>

              <h1 className="mt-8 text-5xl font-extrabold leading-[1.05] tracking-tight text-slate-900 sm:text-6xl lg:text-7xl">
                학생부 기록의
                <span className="mt-2 block text-gradient">숨은 가치를 증명으로</span>
              </h1>

              <p className="mt-8 text-lg font-medium leading-relaxed text-slate-600 sm:text-xl">
                단순 분석을 넘어, 목표 대학 기준에 맞춘 정밀 진단과<br className="hidden sm:block" />
                실행 가능한 워크숍 초안까지 한 번에 연결합니다.
              </p>

              <div className="mt-12 flex flex-wrap justify-center lg:justify-start gap-5">
                <Link
                  to={startHref}
                  onClick={scrollToTop}
                  className="clay-btn-primary group flex items-center gap-3 rounded-2xl px-10 py-5 text-lg shadow-xl"
                >
                  <Rocket size={22} />
                  <span>진단 시작하기</span>
                  <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
                </Link>
                <Link
                  to="/faq"
                  onClick={scrollToTop}
                  className="clay-btn-secondary flex items-center gap-3 rounded-2xl px-10 py-5 text-lg font-bold border border-slate-200 bg-white shadow-sm"
                >
                  시스템 둘러보기
                </Link>
              </div>

              <div className="mt-16 grid grid-cols-3 gap-6 text-center">
                {[
                  { label: "신뢰도 파싱", val: "99%" },
                  { label: "분석 핵심 축", val: "6개" },
                  { label: "맞춤형 피드백", val: "즉시" }
                ].map((stat, i) => (
                  <div key={i} className="animate-rise-in" style={{ animationDelay: `${0.4 + i*0.1}s` }}>
                    <p className="stat-value text-indigo-600/90">{stat.val}</p>
                    <p className="mt-2 text-xs font-bold text-slate-400 uppercase tracking-widest">{stat.label}</p>
                  </div>
                ))}
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="relative"
            >
              <div className="glass-card p-1">
                <div className="overflow-hidden rounded-[1.6rem] bg-white">
                  <div className="bg-slate-50 border-b border-slate-100 px-8 py-6">
                    <div className="flex items-center justify-between">
                      <div className="flex gap-2">
                        <div className="h-3 w-3 rounded-full bg-red-400/80" />
                        <div className="h-3 w-3 rounded-full bg-amber-400/80" />
                        <div className="h-3 w-3 rounded-full bg-emerald-400/80" />
                      </div>
                      <span className="text-[11px] font-black uppercase tracking-widest text-slate-400">Analysis Engine v3.0</span>
                    </div>
                  </div>

                  <div className="p-8 space-y-6">
                    {workflowPanels.map((panel, index) => (
                      <motion.div
                        key={panel.title}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.4 + index * 0.1 }}
                        className="group flex items-start gap-6 rounded-3xl p-6 transition-colors hover:bg-slate-50"
                      >
                        <div className={cn(
                          "flex h-16 w-16 shrink-0 items-center justify-center rounded-[1.25rem] transition-transform group-hover:scale-110 shadow-lg",
                          panel.tone === 'sky' && 'bg-sky-500 text-white shadow-sky-200',
                          panel.tone === 'violet' && 'bg-violet-500 text-white shadow-violet-200',
                          panel.tone === 'emerald' && 'bg-emerald-500 text-white shadow-emerald-200',
                        )}>
                          <panel.icon size={26} strokeWidth={2.5} />
                        </div>
                        <div>
                          <p className="text-xs font-black uppercase tracking-widest text-indigo-400">{panel.eyebrow}</p>
                          <h3 className="mt-1 text-xl font-bold text-slate-900 tracking-tight">{panel.title}</h3>
                          <p className="mt-2 text-[15px] font-medium leading-relaxed text-slate-500">{panel.description}</p>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </div>
              
              {/* Floating element for more life */}
              <div className="absolute -bottom-10 -right-6 h-32 w-32 glass-card flex items-center justify-center animate-float shadow-2xl border-indigo-100">
                <div className="text-center">
                  <p className="text-2xl font-black text-indigo-600">AI</p>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Powered</p>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Principles Section */}
      <section className="mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:px-8">
        <div className="mb-16 text-center max-w-2xl mx-auto">
          <h2 className="text-base font-black uppercase tracking-[0.25em] text-indigo-500">Principles</h2>
          <h3 className="mt-4 text-4xl font-extrabold tracking-tight text-slate-950 sm:text-5xl">
            결과보다 <span className="text-gradient">과정의 연결</span>을 중시합니다
          </h3>
        </div>

        <div className="grid gap-8 md:grid-cols-3">
          {principles.map((item, index) => (
            <div key={item.title} className="glass-card p-10 flex flex-col items-center text-center group">
              <div className="mb-8 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 text-xl font-black group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                0{index + 1}
              </div>
              <h4 className="text-2xl font-bold tracking-tight text-slate-950">{item.title}</h4>
              <p className="mt-4 text-[15px] font-medium leading-relaxed text-slate-500">{item.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-[3rem] bg-indigo-600 px-8 py-20 text-center shadow-2xl">
          <div className="absolute inset-0 -z-10 bg-[linear-gradient(135deg,#6366f1_0%,#4f46e5_40%,#7c3aed_100%)]" />
          <div className="absolute pointer-events-none inset-0 opacity-10 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]" />
          
          <div className="relative z-10">
            <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-5xl">
              지금 당신의 학생부는 어떻게 읽힐까요?<br />
              <span className="opacity-80">데이터로 직접 확인하세요.</span>
            </h2>
            <div className="mt-12 flex flex-wrap justify-center gap-6">
              <Link to={startHref} onClick={scrollToTop} className="rounded-2xl bg-white px-10 py-5 text-lg font-black text-indigo-600 shadow-xl transition-transform hover:-translate-y-1 hover:scale-105 active:scale-95">
                무료 진단 시작하기
              </Link>
              <Link to="/contact" onClick={scrollToTop} className="rounded-2xl border-2 border-white/20 px-10 py-5 text-lg font-black text-white backdrop-blur-sm transition-colors hover:bg-white/10">
                도입 문의
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Summary Footer-like Trust Section */}
      <section className="bg-slate-50 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-12 md:grid-cols-3">
            {trustRows.map((row, i) => (
              <div key={i} className="flex items-center gap-6">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white text-emerald-500 shadow-sm">
                  <ShieldCheck size={24} />
                </div>
                <p className="text-lg font-bold text-slate-700 tracking-tight">{row}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
