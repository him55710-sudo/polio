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

const heroRows = [
  { index: '01', title: '목표 대학과 학과를 먼저 고정', state: 'active' },
  { index: '02', title: '학생부 PDF에서 근거만 추출', state: 'default' },
  { index: '03', title: '강점과 리스크를 바로 분리', state: 'default' },
  { index: '04', title: '초안 작업까지 이어서 진행', state: 'muted' },
];

const storyRows = [
  {
    index: '01',
    label: 'Target',
    title: '대학별 기준부터 맞춥니다',
    description: '같은 학생부라도 대학과 학과가 바뀌면 보는 기준도 달라집니다.',
    icon: Target,
  },
  {
    index: '02',
    label: 'Evidence',
    title: '좋아 보이는 말보다 기록을 먼저 읽습니다',
    description: '학생부 원문에서 분석 가능한 내용만 뽑아 근거로 씁니다.',
    icon: FileSearch,
  },
  {
    index: '03',
    label: 'Direction',
    title: '무엇을 보완할지 바로 보이게 만듭니다',
    description: '강점, 빈칸, 다음 행동을 나눠서 보여 주기 때문에 멈추지 않습니다.',
    icon: Compass,
  },
];

const trustRows = [
  '학생부에 없는 내용은 추천하지 않습니다.',
  '애매한 문장은 먼저 경고합니다.',
  '진단은 바로 다음 작업으로 이어집니다.',
];

export function Landing() {
  const { isAuthenticated } = useAuth();
  const startHref = isAuthenticated ? '/app/diagnosis' : '/auth';

  const scrollToTop = () => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  };

  return (
    <div className="bg-[linear-gradient(180deg,#f7fbff_0%,#edf5ff_100%)] text-slate-900">
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_14%_16%,rgba(39,169,255,0.22),transparent_28%),radial-gradient(circle_at_90%_8%,rgba(60,102,255,0.2),transparent_28%)]" />
        <div className="pointer-events-none absolute -left-28 top-24 h-80 w-80 rounded-full border border-[#c8defd]" />
        <div className="pointer-events-none absolute -right-20 bottom-10 h-72 w-72 rounded-full border border-[#c8defd]" />

        <div className="relative mx-auto max-w-7xl px-4 pb-20 pt-16 sm:px-6 lg:px-8 lg:pb-24 lg:pt-24">
          <div className="grid items-end gap-12 lg:grid-cols-[0.92fr_1.08fr]">
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              className="max-w-2xl"
            >
              <p className="inline-flex items-center gap-2 rounded-full border border-[#d5e3ff] bg-white/80 px-4 py-2 text-[11px] font-black uppercase tracking-[0.22em] text-[#2f5db6] shadow-[0_10px_24px_rgba(24,66,170,0.1)] backdrop-blur">
                <Sparkles size={13} />
                Admission workflow
              </p>

              <h1 className="mt-8 text-4xl font-black leading-[1.02] tracking-tight text-slate-900 sm:text-5xl lg:text-[5.2rem]">
                입시 준비를
                <span className="mt-2 block bg-[linear-gradient(135deg,#1d4fff_0%,#2da3ff_100%)] bg-clip-text text-transparent">더 적게 읽고</span>
                더 정확하게
              </h1>

              <p className="mt-6 max-w-lg text-base font-medium leading-8 text-slate-600 sm:text-lg">
                대학과 학과를 맞추고, 학생부를 읽고, 바로 다음 행동까지 연결합니다.
              </p>

              <div className="mt-10 flex flex-wrap gap-4">
                <Link
                  to={startHref}
                  onClick={scrollToTop}
                  className={cn(buttonClassName({ variant: 'primary', size: 'lg' }), 'rounded-2xl px-8')}
                >
                  <Rocket size={18} />
                  무료 진단 시작하기
                </Link>
                <Link
                  to="/contact"
                  onClick={scrollToTop}
                  className={cn(
                    buttonClassName({ variant: 'ghost', size: 'lg' }),
                    'rounded-2xl border border-[#d4e2ff] bg-white/78 px-7 text-[#2f5db6] hover:bg-white hover:text-[#1d4fff]',
                  )}
                >
                  도입 문의
                </Link>
              </div>

              <div className="mt-10 flex flex-wrap gap-3 text-sm font-bold text-[#2f4f8f]">
                <span className="rounded-full border border-[#d7e5ff] bg-white/82 px-4 py-2 shadow-[0_8px_18px_rgba(24,66,170,0.08)]">대학·학과 기준</span>
                <span className="rounded-full border border-[#d7e5ff] bg-white/82 px-4 py-2 shadow-[0_8px_18px_rgba(24,66,170,0.08)]">학생부 PDF 분석</span>
                <span className="rounded-full border border-[#d7e5ff] bg-white/82 px-4 py-2 shadow-[0_8px_18px_rgba(24,66,170,0.08)]">초안 연결</span>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.58, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
              className="relative min-h-[420px] lg:min-h-[520px]"
            >
              <div className="absolute inset-0 rounded-[2.5rem] border border-[#d8e6ff] bg-white/78 shadow-[0_24px_52px_rgba(24,66,170,0.14)] backdrop-blur-xl" />
              <div className="absolute right-6 top-3 text-[7rem] font-black tracking-[-0.08em] text-[#dce8ff] sm:text-[9rem]">
                04
              </div>
              <div className="absolute left-8 top-8 h-24 w-24 rounded-full bg-cyan-300/30 blur-3xl" />

              <div className="relative flex h-full flex-col justify-center gap-3 px-5 py-6 sm:px-7 lg:px-9">
                {heroRows.map((row, index) => (
                  <motion.div
                    key={row.index}
                    initial={{ opacity: 0, x: 24 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.32, delay: 0.16 + index * 0.08 }}
                    className={cn(
                      'flex items-center justify-between rounded-[1.6rem] border px-5 py-5',
                      row.state === 'active' && 'border-[#9ad8ff] bg-[#e8f6ff] text-[#2050a9]',
                      row.state === 'default' && 'border-[#d8e6ff] bg-white/84 text-[#2f4f8f]',
                      row.state === 'muted' && 'border-[#d8e6ff] bg-[#f2f7ff] text-[#7091c8]',
                    )}
                  >
                    <div>
                      <p className="text-[10px] font-black uppercase tracking-[0.2em] opacity-70">Step {row.index}</p>
                      <p className="mt-2 text-base font-black sm:text-lg">{row.title}</p>
                    </div>
                    <span className="text-2xl font-black tracking-[-0.08em] opacity-35 sm:text-3xl">{row.index}</span>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8 lg:py-24">
        <div className="grid gap-10 lg:grid-cols-[0.78fr_1.22fr]">
          <div className="lg:sticky lg:top-24 lg:self-start">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-[#2f5db6]">Sequence</p>
            <h2 className="mt-4 text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">
              한 화면에서 끝내지 않고
              <span className="mt-2 block bg-[linear-gradient(135deg,#1d4fff_0%,#2da3ff_100%)] bg-clip-text text-transparent">준비 흐름으로 끌고 갑니다</span>
            </h2>
            <p className="mt-5 max-w-sm text-base font-medium leading-8 text-slate-600">
              아래로 내려갈수록 무엇을 먼저 해야 하는지가 더 선명해집니다.
            </p>
          </div>

          <div className="space-y-4">
            {storyRows.map((row, index) => (
              <motion.article
                key={row.index}
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.34, delay: index * 0.06 }}
                className="rounded-[2rem] border border-[#d8e6ff] bg-white/86 px-6 py-6 shadow-[0_16px_38px_rgba(24,66,170,0.1)] sm:px-7"
              >
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#eaf2ff] text-[#1d4fff]">
                    <row.icon size={20} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-[11px] font-black uppercase tracking-[0.2em] text-[#2f5db6]">{row.label}</p>
                      <span className="text-2xl font-black tracking-[-0.08em] text-slate-200">{row.index}</span>
                    </div>
                    <h3 className="mt-2 text-2xl font-black tracking-tight text-slate-900">{row.title}</h3>
                    <p className="mt-3 text-sm font-medium leading-7 text-slate-600">{row.description}</p>
                  </div>
                </div>
              </motion.article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-slate-200/80 bg-white/86 backdrop-blur-sm">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-16 sm:px-6 lg:grid-cols-[0.92fr_1.08fr] lg:px-8 lg:py-22">
          <div className="rounded-[2.2rem] bg-[linear-gradient(135deg,#1d4fff_0%,#2da3ff_100%)] px-7 py-8 text-white shadow-[0_28px_70px_rgba(29,79,255,0.28)] sm:px-8 sm:py-9">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-cyan-100">Trust</p>
            <h3 className="mt-4 text-3xl font-black tracking-tight">
              입시 서비스답게
              <span className="mt-2 block text-cyan-100">기준부터 분명하게</span>
            </h3>
          </div>

          <div className="grid gap-4">
            {trustRows.map((row, index) => (
              <motion.div
                key={row}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
                className="flex items-center gap-4 rounded-[1.8rem] border border-[#d8e6ff] bg-[#f8fbff] px-6 py-5"
              >
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-[#1d4fff] shadow-sm">
                  {index === 0 ? <ShieldCheck size={19} /> : <ArrowRight size={18} />}
                </div>
                <p className="text-base font-bold tracking-tight text-slate-900">{row}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-slate-200 bg-[linear-gradient(180deg,#eef5ff_0%,#e2eeff_100%)]">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8 lg:py-22">
          <div className="relative overflow-hidden rounded-[2.5rem] border border-[#d3e2ff] bg-white/88 px-8 py-14 text-center shadow-[0_22px_48px_rgba(24,66,170,0.14)] backdrop-blur sm:px-12 sm:py-20">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_30%,rgba(34,211,238,0.2),transparent_34%),radial-gradient(circle_at_80%_70%,rgba(59,130,246,0.18),transparent_34%)]" />
            <div className="relative z-10 mx-auto max-w-3xl">
              <p className="text-xs font-black uppercase tracking-[0.2em] text-[#2f5db6]">Start now</p>
              <h2 className="mt-5 text-3xl font-black tracking-tight text-slate-900 sm:text-4xl lg:text-5xl">
                더 많이 읽기보다
                <span className="mt-2 block bg-[linear-gradient(135deg,#1d4fff_0%,#2da3ff_100%)] bg-clip-text text-transparent">바로 움직이는 준비로</span>
              </h2>
              <p className="mt-5 text-base font-medium leading-8 text-slate-600 sm:text-lg">
                생기부를 읽고, 기준을 맞추고, 다음 행동까지 바로 이어 가세요.
              </p>
              <div className="mt-9 flex flex-wrap justify-center gap-4">
                <Link to={startHref} onClick={scrollToTop} className={cn(buttonClassName({ variant: 'primary', size: 'lg' }), 'rounded-2xl px-8')}>
                  무료 진단 시작하기
                </Link>
                <Link
                  to="/faq"
                  onClick={scrollToTop}
                  className={cn(
                    buttonClassName({ variant: 'ghost', size: 'lg' }),
                    'rounded-2xl border border-[#d5e3ff] bg-white/76 px-8 text-[#24498f] hover:bg-white hover:text-[#1d4fff]',
                  )}
                >
                  더 알아보기
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
