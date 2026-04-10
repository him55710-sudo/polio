import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Compass,
  FileSearch,
  PenTool,
  Rocket,
  ShieldCheck,
  Sparkles,
  Target,
  Zap,
} from 'lucide-react';
import { FaqAccordion } from '../components/FaqAccordion';
import { faqPreviewItems } from '../content/faq';
import { useAuth } from '../contexts/AuthContext';
import { buttonClassName } from '../components/ui';
import { cn } from '../lib/cn';

const workflowItems = [
  {
    title: '1. 목표 세팅',
    description: '대학과 전공 목표를 먼저 고정해 AI 진단 기준을 명확히 맞춥니다.',
    icon: Target,
  },
  {
    title: '2. 학생부 업로드',
    description: 'PDF를 올리면 핵심 근거를 추출하고 과장 가능 문장을 먼저 걸러냅니다.',
    icon: FileSearch,
  },
  {
    title: '3. 진단 결과 확인',
    description: '강점·보완점·다음 액션을 근거와 함께 바로 확인할 수 있습니다.',
    icon: Compass,
  },
  {
    title: '4. 문서 초안 작성',
    description: '진단 결과를 문서 흐름으로 연결해 실제 제출 가능한 초안으로 이어집니다.',
    icon: PenTool,
  },
];

const trustPoints = [
  '근거 없는 문장은 자동으로 경고해요.',
  '합격 보장 표현 대신 다음 행동을 제시해요.',
  '학생 기록 범위를 넘어선 과장 작성을 막아요.',
];

const pricingPlans = [
  {
    name: 'Free',
    badge: '기본',
    monthlyPrice: '₩0',
    originalPrice: null,
    description: '서비스를 처음 경험해 보는 학생을 위한 시작 플랜',
    highlights: ['진단 체험', '게스트 미리보기', '문의 채널 이용'],
    cta: '무료로 시작',
    href: '/auth',
    featured: false,
  },
  {
    name: 'Plus',
    badge: '추천',
    monthlyPrice: '₩5,900',
    originalPrice: '정가 예정 ₩9,900',
    description: '준비 루틴을 꾸준히 이어가고 싶은 학생용 플랜',
    highlights: ['심화 진단', '진행 기록 관리', '우선 문의 지원'],
    cta: 'Plus 시작',
    href: '/auth?plan=plus',
    featured: true,
  },
  {
    name: 'Pro',
    badge: '고급',
    monthlyPrice: '₩9,900',
    originalPrice: '정가 예정 ₩15,900',
    description: '장기 준비와 정교한 관리가 필요한 학생용 플랜',
    highlights: ['고급 분석 흐름', '확장 문서 워크플로우', '전용 안내 채널'],
    cta: 'Pro 시작',
    href: '/auth?plan=pro',
    featured: false,
  },
];

export function Landing() {
  const { isAuthenticated } = useAuth();
  const startHref = isAuthenticated ? '/app' : '/auth';

  const scrollToTop = () => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  };

  return (
    <div className="bg-slate-50 text-slate-900">
      <section className="relative overflow-hidden border-b border-slate-200 bg-white">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_22%,rgba(0,74,173,0.08),transparent_40%),radial-gradient(circle_at_82%_18%,rgba(59,130,246,0.1),transparent_36%),linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)]" />
        
        {/* Subtle Decorative Elements */}
        <div className="pointer-events-none absolute -left-28 top-24 h-72 w-72 rounded-full border border-[#004aad]/10" />
        <div className="pointer-events-none absolute -right-24 bottom-10 h-64 w-64 rounded-full border border-[#004aad]/10" />

        <div className="relative mx-auto max-w-7xl px-4 pb-20 pt-16 sm:px-6 sm:pb-24 lg:px-8 lg:pt-28">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="grid gap-16 lg:grid-cols-[1.1fr_0.9fr]"
          >
            <div>
              <p className="inline-flex items-center gap-2.5 rounded-full border border-[#004aad]/10 bg-[#004aad]/5 px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-[#004aad]">
                <Sparkles size={14} className="animate-pulse" />
                Evidence First Workflow
              </p>
              <h1 className="mt-8 max-w-3xl text-4xl font-black leading-[1.15] tracking-tight text-slate-900 sm:text-5xl lg:text-6xl">
                막막한 입시 준비를
                <span className="mt-2 block bg-gradient-to-r from-[#004aad] via-[#1d72e8] to-[#0ea5e9] bg-clip-text text-transparent pb-1">근거 중심 실행 플랜</span>
                으로 바꿔줍니다
              </h1>
              <p className="mt-8 max-w-2xl text-lg font-medium leading-relaxed text-slate-600 sm:text-xl">
                목표 설정부터 학생부 분석, 진단 결과, 문서 초안까지. <br className="hidden md:block" />
                한 화면에서 바로 이어지는 흐름으로 불안한 준비 과정을 <br className="hidden md:block" />
                확신 있는 발걸음으로 바꿉니다.
              </p>

              <div className="mt-10 flex flex-wrap gap-4">
                <Link
                  to={startHref}
                  onClick={scrollToTop}
                  className={cn(
                    buttonClassName({ variant: 'primary', size: 'lg' }), 
                    'rounded-2xl px-10 py-7 text-lg shadow-2xl shadow-[#004aad]/20 bg-[#004aad] hover:bg-[#003882] transition-all hover:scale-[1.02] active:scale-[0.98]'
                  )}
                >
                  <Rocket size={20} className="mr-1" />
                  지금 시작하기
                </Link>
                <Link
                  to="/contact"
                  onClick={scrollToTop}
                  className={cn(
                    buttonClassName({ variant: 'ghost', size: 'lg' }),
                    'rounded-2xl border border-slate-200 bg-white px-10 py-7 text-lg text-slate-700 hover:bg-slate-50 transition-all hover:border-slate-300',
                  )}
                >
                  무료 체험하기
                </Link>
              </div>

              <div className="mt-12 grid max-w-3xl gap-4 sm:grid-cols-3">
                {[
                  { label: '진단 흐름', value: '4 STEP', icon: Zap },
                  { label: '파일 업로드', value: 'PDF 지원', icon: FileSearch },
                  { label: '결과 연결', value: '문서 초안', icon: BookOpen },
                ].map(item => (
                  <div key={item.label} className="group rounded-2xl border border-slate-100 bg-white p-5 shadow-sm transition-all hover:border-[#004aad]/20 hover:shadow-md">
                    <p className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-slate-400 group-hover:text-[#004aad]">
                      <item.icon size={14} />
                      {item.label}
                    </p>
                    <p className="mt-2 text-xl font-extrabold text-slate-800">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="absolute -inset-4 rounded-[40px] bg-gradient-to-br from-[#004aad]/10 via-transparent to-[#004aad]/5 blur-2xl" />
              
              <div className="relative h-full rounded-[32px] border border-slate-100 bg-white p-8 shadow-[0_32px_80px_rgba(0,74,173,0.08)] sm:p-10">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#004aad]">실행 프리뷰</p>
                  <div className="flex gap-1.5">
                    <div className="h-2.5 w-2.5 rounded-full bg-slate-100" />
                    <div className="h-2.5 w-2.5 rounded-full bg-slate-100" />
                    <div className="h-2.5 w-2.5 rounded-full bg-slate-100" />
                  </div>
                </div>
                
                <h2 className="mt-5 text-2xl font-black tracking-tight text-slate-900">오늘 해야 할 일만 선명하게</h2>
                <p className="mt-3 text-base font-medium leading-relaxed text-slate-500">
                  합격을 보장하는 과장 대신, 현재 기록에서 가능한 다음 액션을 우선순위로 제안합니다.
                </p>

                <div className="mt-8 space-y-4">
                  {[
                    { text: '학생부에서 근거 추출 완료', status: 'completed' },
                    { text: '강점/보완점 진단 결과 생성', status: 'completed' },
                    { text: '다음 행동 3개 자동 제안', status: 'active' },
                    { text: '초안 작성 워크플로우 연결', status: 'pending' },
                  ].map((item, idx) => (
                    <div key={item.text} className={cn(
                      "flex items-center gap-4 rounded-2xl border px-5 py-4 transition-all",
                      item.status === 'completed' ? "border-slate-50 bg-slate-50/50 text-slate-400" : 
                      item.status === 'active' ? "border-[#004aad]/20 bg-[#004aad]/5 text-[#004aad] shadow-sm" :
                      "border-slate-50 bg-white text-slate-400 opacity-60"
                    )}>
                      {item.status === 'completed' ? <CheckCircle2 size={18} /> : 
                       item.status === 'active' ? <Sparkles size={18} className="animate-pulse" /> : 
                       <div className="h-[18px] w-[18px] rounded-full border-2 border-slate-200" />}
                      <span className="text-sm font-bold">{item.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
        <div className="grid gap-6 lg:grid-cols-4">
          {workflowItems.map(item => (
            <article key={item.title} className="group rounded-[24px] border border-slate-100 bg-white p-6 shadow-sm transition-all hover:-translate-y-1 hover:border-[#004aad]/20 hover:shadow-xl">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#004aad]/5 text-[#004aad] transition-colors group-hover:bg-[#004aad] group-hover:text-white">
                <item.icon size={24} />
              </div>
              <p className="mt-5 text-lg font-bold text-slate-900 leading-tight">
                {item.title}
              </p>
              <p className="mt-3 text-sm font-medium leading-relaxed text-slate-500 break-keep">{item.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-slate-100 bg-slate-50/50">
        <div className="mx-auto grid max-w-7xl gap-12 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-2 lg:px-8">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#004aad]">핵심 가치</p>
            <h2 className="mt-4 text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">안전하게, 그러나 빠르게</h2>
            <p className="mt-6 text-lg font-medium leading-relaxed text-slate-600">
              Uni Foli는 그럴듯한 문장을 만드는 도구가 아니라, 실제 기록 기반으로 다음 행동을 좁혀주는 실행 도구입니다.
            </p>
            <div className="mt-8 space-y-4">
              {trustPoints.map(point => (
                <div key={point} className="flex items-start gap-4 rounded-3xl border border-slate-100 bg-white p-5 shadow-sm">
                  <div className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
                    <CheckCircle2 size={14} />
                  </div>
                  <p className="text-sm font-bold leading-relaxed text-slate-700 break-keep">{point}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[40px] border border-[#004aad]/10 bg-gradient-to-br from-[#004aad]/5 via-white to-[#004aad]/5 p-8 shadow-sm sm:p-10">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#004aad]">Outcome</p>
            <h3 className="mt-4 text-2xl font-black tracking-tight text-slate-900">진단에서 작성까지 끊기지 않는 흐름</h3>
            <ul className="mt-8 space-y-4">
              {[
                '근거-문장 매핑으로 결과 신뢰도 확보',
                '부족한 포인트를 즉시 보완 액션으로 전환',
                '워크숍/에디터로 바로 이어지는 작성 동선',
              ].map(item => (
                <li key={item} className="flex items-center gap-4 rounded-2xl border border-slate-50 bg-white px-5 py-4 text-sm font-bold text-slate-700 shadow-sm transition-all hover:bg-slate-50">
                  <div className="h-2 w-2 rounded-full bg-[#004aad]" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
        <div className="rounded-[40px] border border-amber-100 bg-gradient-to-br from-amber-50/30 via-white to-orange-50/20 p-8 shadow-sm sm:p-12 lg:p-16">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-amber-600">
                <Sparkles size={14} />
                출시 기념 요금
              </p>
              <h2 className="mt-3 text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">요금제 안내</h2>
              <p className="mt-3 text-base font-medium text-slate-500 break-keep">정식 오픈 전 얼리버드 혜택으로 시작하세요.</p>
            </div>
            <p className="text-sm font-bold text-slate-400">월 결제 기준 · VAT 포함</p>
          </div>

          <div className="mt-10 grid gap-6 lg:grid-cols-3">
            {pricingPlans.map(plan => (
              <article
                key={plan.name}
                className={cn(
                  'relative flex flex-col rounded-[32px] border bg-white p-7 shadow-sm transition-all hover:shadow-xl sm:p-8',
                  plan.featured ? 'border-[#004aad]/20 scale-[1.02] z-10 shadow-xl shadow-[#004aad]/5' : 'border-slate-100',
                )}
              >
                {plan.featured && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 rounded-full bg-[#004aad] px-4 py-1.5 text-[10px] font-black uppercase tracking-widest text-white shadow-xl">
                    Most Popular
                  </div>
                )}
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-400">{plan.name}</p>
                    <div className="mt-3 flex items-baseline gap-1">
                      <span className="text-4xl font-black tracking-tight text-slate-900">{plan.monthlyPrice}</span>
                    </div>
                    {plan.originalPrice ? (
                      <p className="mt-2 text-xs font-bold text-rose-500 line-through opacity-60">{plan.originalPrice}</p>
                    ) : (
                      <p className="mt-2 text-xs font-bold text-emerald-600">항상 무료</p>
                    )}
                  </div>
                </div>

                <p className="mt-6 text-sm font-medium leading-relaxed text-slate-500 break-keep">{plan.description}</p>
                
                <div className="my-8 h-px bg-slate-100 w-full" />

                <ul className="flex-1 space-y-4">
                  {plan.highlights.map(highlight => (
                    <li key={highlight} className="flex items-start gap-3 text-sm font-bold text-slate-700">
                      <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#004aad]/5 text-[#004aad]">
                        <CheckCircle2 size={12} />
                      </div>
                      <span className="break-keep">{highlight}</span>
                    </li>
                  ))}
                </ul>

                <Link
                  to={plan.href}
                  onClick={scrollToTop}
                  className={cn(
                    buttonClassName({
                      variant: plan.featured ? 'primary' : 'secondary',
                      size: 'lg',
                      fullWidth: true,
                    }),
                    'mt-10 rounded-2xl py-6 font-bold transition-all',
                    plan.featured ? 'bg-[#004aad] hover:bg-[#003882] shadow-lg shadow-[#004aad]/20' : 'bg-slate-50 hover:bg-slate-100 text-slate-700'
                  )}
                >
                  {plan.cta}
                  <ArrowRight size={18} className="ml-1" />
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between sm:gap-6">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-400">FAQ</p>
            <h2 className="mt-3 text-3xl font-black tracking-tight text-slate-900">자주 묻는 질문</h2>
          </div>
          <Link
            to="/faq"
            onClick={scrollToTop}
            className="inline-flex items-center gap-2 rounded-[20px] border border-slate-200 bg-white px-6 py-3 text-sm font-bold text-slate-700 shadow-sm transition-all hover:bg-slate-50"
          >
            전체 보기
            <ArrowRight size={16} />
          </Link>
        </div>
        <div className="mt-10">
          <FaqAccordion items={faqPreviewItems} initialOpenId={faqPreviewItems[0]?.id} compact />
        </div>
      </section>

      <section className="border-t border-slate-100 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
          <div className="relative overflow-hidden rounded-[40px] bg-slate-900 px-8 py-16 text-center sm:px-16 sm:py-24">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_30%,rgba(0,74,173,0.3),transparent_40%),radial-gradient(circle_at_80%_70%,rgba(59,130,246,0.2),transparent_40%)]" />
            <div className="relative z-10">
              <p className="mx-auto text-xs font-bold uppercase tracking-[0.2em] text-[#004aad]/60">Start Now</p>
              <h2 className="mx-auto mt-6 text-3xl font-black tracking-tight text-white sm:text-4xl lg:text-5xl break-keep">
                오늘의 준비를 실행 가능한 <br className="hidden md:block" /> 계획으로 바꿔보세요
              </h2>
              <p className="mx-auto mt-6 max-w-2xl text-lg font-medium leading-relaxed text-slate-400 break-keep">
                기록 업로드부터 진단, 문서 초안 연결까지 <br className="hidden md:block" /> 
                한 번에 이어지는 몰입의 워크플로우를 경험하세요.
              </p>
              <div className="mt-12 flex flex-wrap justify-center gap-4">
                <Link
                  to={startHref}
                  onClick={scrollToTop}
                  className={cn(buttonClassName({ variant: 'primary', size: 'lg' }), 'rounded-[20px] px-10 py-7 text-lg shadow-2xl shadow-[#004aad]/40 bg-[#004aad] hover:bg-[#003882] sm:px-12')}
                >
                  <BookOpen size={20} className="mr-1" />
                  준비 시작하기
                </Link>
                <Link
                  to="/contact?type=partnership"
                  onClick={scrollToTop}
                  className={cn(
                    buttonClassName({ variant: 'ghost', size: 'lg' }),
                    'rounded-[20px] border border-white/10 bg-white/5 px-10 py-7 text-lg text-white hover:bg-white/10 sm:px-12',
                  )}
                >
                  제휴 문의
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
