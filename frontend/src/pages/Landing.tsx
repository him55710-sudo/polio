import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import { ArrowDown, ArrowRight, Compass, FileSearch, Layers3, Rocket, Sparkles, Target } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';


const quickMajors = ['건축', '컴공', '바이오', '경영', '사회과학', '디자인'];

const quickFeatures = [
  {
    title: 'PDF 진단',
    subtitle: '파일 업로드',
    icon: FileSearch,
    accent: 'from-indigo-600 to-indigo-500',
    href: '/app/diagnosis',
  },
  {
    title: '트렌드 탐색',
    subtitle: '전공 주제칩',
    icon: Compass,
    accent: 'from-indigo-500 to-indigo-400',
    href: '/app/trends',
  },
  {
    title: '워크숍 설계',
    subtitle: '실행 계획',
    icon: Layers3,
    accent: 'from-indigo-400 to-blue-400',
    href: '/app/workshop',
  },
  {
    title: '결과 출력',
    subtitle: '문서 정리',
    icon: Target,
    accent: 'from-blue-400 to-sky-400',
    href: '/app/workshop',
  },
];

export function Landing() {
  const { isAuthenticated } = useAuth();
  const startHref = isAuthenticated ? '/app/diagnosis' : '/auth';

  const scrollToTop = () => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  };

  return (
    <div className="bg-transparent text-slate-900 selection:bg-indigo-100">
      <section className="relative overflow-hidden pt-14 sm:pt-20 lg:pt-24">


        <div className="mx-auto grid max-w-7xl gap-10 px-4 pb-14 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-14 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.45 }}
            transition={{ duration: 0.48 }}
            className="space-y-6"
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-white/92 px-3 py-1.5 text-xs font-black text-indigo-700 shadow-sm">
              <Sparkles size={14} />
              트렌드·진단·워크숍 코파일럿
            </div>

            <h1 className="text-4xl font-black leading-tight tracking-tight sm:text-5xl lg:text-6xl">
              말은 짧게
              <br />
              <span className="bg-gradient-to-r from-indigo-600 to-blue-500 bg-clip-text text-transparent">
                실행은 빠르게
              </span>
            </h1>

            <div className="flex flex-wrap gap-2">
              {quickMajors.map((major) => (
                <span
                  key={major}
                  className="rounded-full border border-slate-200 bg-white/92 px-3 py-1 text-sm font-bold text-slate-700 shadow-[0_8px_16px_-14px_rgba(15,23,42,0.5)]"
                >
                  {major}
                </span>
              ))}
            </div>

            <div className="flex flex-wrap gap-3">
              <Link to={startHref} onClick={scrollToTop} className="btn-primary inline-flex items-center gap-2">
                <Rocket size={16} />
                시작
                <ArrowRight size={14} />
              </Link>
              <Link to="/app/trends" onClick={scrollToTop} className="btn-secondary inline-flex items-center gap-2">
                트렌드
                <ArrowRight size={14} />
              </Link>
              <Link to="/app/workshop" onClick={scrollToTop} className="btn-secondary inline-flex items-center gap-2">
                워크숍
                <ArrowRight size={14} />
              </Link>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, amount: 0.35 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="relative"
          >
            <div className="relative overflow-hidden rounded-[2.5rem] border border-slate-200 bg-white p-10 shadow-xl shadow-blue-50/50 sm:p-14 flex flex-col items-center justify-center h-full min-h-[320px]">
              {/* Subtle background element */}
              <div className="absolute top-0 right-0 -mr-16 -mt-16 h-64 w-64 rounded-full bg-blue-50/50 blur-3xl opacity-60" />
              <div className="absolute bottom-0 left-0 -ml-16 -mb-16 h-64 w-64 rounded-full bg-indigo-50/50 blur-3xl opacity-60" />
              
              <div className="relative z-10 space-y-6 text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 text-[#3182f6]">
                  <Layers3 size={32} strokeWidth={2.5} />
                </div>
                <h2 className="text-3xl font-black tracking-tight text-[#191f28] sm:text-4xl">
                  입시 전략의 새로운 패러다임
                </h2>
                <p className="text-lg font-medium leading-relaxed text-[#4e5968] max-w-[280px] mx-auto">
                  여러분의 학생부 분석부터 워크숍 기획까지, <span className="font-black text-[#3182f6]">UniFoli</span>가 함께합니다.
                </p>
              </div>
            </div>
          </motion.div>
        </div>

        <div className="mb-12" />
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-12 sm:px-6 lg:px-8">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {quickFeatures.map((item, index) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.35 }}
              transition={{ duration: 0.42, delay: index * 0.06 }}
            >
              <Link
                to={item.href}
                onClick={scrollToTop}
                className="group tilt-3d block rounded-3xl border border-white/70 bg-white/84 p-4 shadow-[0_20px_42px_-30px_rgba(15,23,42,0.5)] backdrop-blur-md"
              >
                <div className={`relative overflow-hidden rounded-2xl bg-gradient-to-br p-4 text-white shadow-inner ${item.accent}`}>
                  <item.icon size={16} />
                  <p className="mt-8 text-lg font-black">{item.title}</p>
                  <p className="text-xs font-bold text-white/85">{item.subtitle}</p>
                  <div className="absolute -bottom-5 -right-5 h-20 w-20 rounded-full bg-white/18 blur-md" />
                </div>
                <div className="mt-4 inline-flex items-center gap-2 text-sm font-extrabold text-slate-700 transition group-hover:text-slate-900">
                  열기
                  <ArrowRight size={14} />
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  );
}
