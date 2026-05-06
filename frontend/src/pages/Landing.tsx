import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import {
  ArrowRight,
  BookOpenCheck,
  Check,
  ClipboardCheck,
  FileSearch,
  MessageSquareText,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { PUBLIC_DESIGN_VARIANT_STORAGE_KEY, getPublicDesignVariant } from '../lib/publicDesignVariant';
import { LandingPortalVariant } from './LandingPortalVariant';

const workflowSteps = [
  {
    title: '생기부 업로드',
    copy: 'PDF를 올리면 학생명, 학교, 세특·진로·동아리 기록을 먼저 구조화합니다.',
  },
  {
    title: '근거 기반 진단',
    copy: '전공 연결 근거, 탐구 깊이, 기록 공백, 설명 가능성을 문장 단위로 확인합니다.',
  },
  {
    title: '보완 탐구 추천',
    copy: '부족한 근거를 채울 수 있는 세특·탐구 주제를 학생 수준에 맞게 제안합니다.',
  },
  {
    title: '보고서·면접 실행',
    copy: '선택한 주제를 워크숍에서 보고서 초안, 면접 질문, 후속 탐구로 이어갑니다.',
  },
];

const pricingPlans = [
  {
    name: 'Free',
    price: '0원',
    description: '처음 방향을 확인하는 체험 진단',
    outputs: ['샘플 진단 흐름', '생기부 요약', '대표 강점 2개', '기본 탐구 아이디어'],
    cta: '무료로 시작',
    href: '/auth',
  },
  {
    name: 'Pro',
    price: '23,900원',
    description: '생기부를 실제 보완 계획으로 바꾸는 리포트',
    outputs: ['7쪽 진단 리포트', '핵심 세특 분석', '전공 연결망', '추천 탐구 주제 8개', '보완 액션 플랜'],
    cta: 'Pro로 진단',
    href: '/auth',
    featured: true,
  },
  {
    name: 'Ultra',
    price: '49,900원',
    description: '진단 이후 보고서와 면접까지 이어가는 실행 패키지',
    outputs: ['Pro 전체 포함', '면접 질문 20개', '보고서 개요·초안', '학년별 후속 탐구 설계', '워크숍 저장·재작업'],
    cta: 'Ultra로 실행',
    href: '/auth',
  },
];

export function Landing() {
  const [designVariant, setDesignVariant] = React.useState(() => getPublicDesignVariant());

  React.useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key === PUBLIC_DESIGN_VARIANT_STORAGE_KEY) {
        setDesignVariant(getPublicDesignVariant());
      }
    };

    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  if (designVariant === 'portal') {
    return <LandingPortalVariant />;
  }

  return <LandingClassic />;
}

function LandingClassic() {
  const { isAuthenticated } = useAuth();
  const startHref = isAuthenticated ? '/app/diagnosis' : '/auth';

  return (
    <div className="bg-[#fcfdff] text-slate-900 relative overflow-hidden min-h-screen">
      
      {/* 🔮 사이버네틱 다이내믹 메쉬 오라 광선 */}
      <div className="absolute top-[-10%] left-[-10%] h-[700px] w-[700px] rounded-full bg-gradient-to-br from-indigo-200/40 to-transparent blur-[120px] pointer-events-none" />
      <div className="absolute top-[20%] right-[-10%] h-[800px] w-[800px] rounded-full bg-gradient-to-bl from-purple-200/35 to-transparent blur-[140px] pointer-events-none" />
      <div className="absolute bottom-[10%] left-[10%] h-[600px] w-[600px] rounded-full bg-gradient-to-tr from-sky-200/30 to-transparent blur-[110px] pointer-events-none" />

      {/* Hero Section */}
      <section className="relative z-10 py-12 lg:py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-8 grid gap-16 lg:grid-cols-[1fr_1fr] items-center">
          
          {/* 좌측 텍스트 인트로 영역 */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
            className="space-y-8"
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-indigo-50/40 p-1.5 pr-4 text-xs font-black text-indigo-700 shadow-sm backdrop-blur-md">
              <span className="flex h-6 items-center justify-center rounded-full bg-indigo-600 px-3 text-[10px] font-black text-white uppercase tracking-wider">AI ENGINE v2.5</span>
              <span className="font-bold tracking-tight">기록된 사실의 근거(Citation)와 심화 탐구 방향 진단</span>
            </div>

            <h1 className="text-4xl font-black leading-[1.08] tracking-tight sm:text-6xl text-slate-900">
              생기부를 디코딩하고,
              <span className="block mt-2 bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                보완할 후속 탐구를 그립니다
              </span>
            </h1>

            <p className="max-w-2xl text-base sm:text-lg font-bold leading-relaxed text-slate-500">
              단순한 합격 등급 판정이 아닌, 학생이 지닌 기록의 완성도를 문장 단위로 스캔하여 
              설명 가능한 전공 연결망과 심화 탐구 주제를 제안하는 고밀도 입시 진단 플랫폼입니다.
            </p>

            <div className="flex flex-wrap gap-4 pt-2">
              <Link
                to={startHref}
                className="group inline-flex items-center gap-2 rounded-2xl bg-indigo-600 px-7 py-4.5 text-base font-black text-white shadow-lg shadow-indigo-200 hover:bg-indigo-700 hover:shadow-xl hover:shadow-indigo-300 hover:-translate-y-0.5 transition-all duration-300"
              >
                나의 학생부 스캔 시작하기
                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                to="/help/student-record-pdf"
                className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-7 py-4.5 text-base font-black text-slate-600 hover:bg-slate-50 hover:border-slate-300 hover:-translate-y-0.5 transition-all duration-300 shadow-sm"
              >
                PDF 발급 안내 가이드
              </Link>
            </div>
          </motion.div>

          {/* 우측 실시간 액티브 리포트 시뮬레이션 프리뷰 */}
          <motion.div
            initial={{ opacity: 0, scale: 0.94, y: 30 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2, ease: 'easeOut' }}
            className="relative"
          >
            {/* 후광 장식 */}
            <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500 to-purple-500 rounded-[40px] opacity-10 blur-2xl -z-10" />
            <EvidenceReportPreview />
          </motion.div>

        </div>
      </section>

      {/* Core Workflow Section */}
      <WorkflowSection />

      {/* Evidence First Section */}
      <section className="relative z-10 border-y border-slate-100 bg-white py-20">
        <div className="mx-auto max-w-7xl px-6 lg:px-8 grid gap-12 lg:grid-cols-[1fr_1.1fr] items-center">
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-[10px] font-black text-indigo-600 uppercase tracking-wider">EVIDENCE-BASED ENGINE</span>
            <h2 className="mt-4 text-3xl font-black tracking-tight sm:text-4xl text-slate-900 leading-tight">
              추측된 예측 점수보다 중요한 것은<br />기록의 문학적 근거와 완결성입니다
            </h2>
            <p className="mt-5 text-sm sm:text-base font-bold leading-relaxed text-slate-500">
              Uni Foli는 단순 확률 기반 예측에서 탈피해, 학생부 내 서술된 물리적 근거와 학업 성취 수준을 비교 검증합니다.
              공백 지점을 찾아내고, 신뢰도 높은 다음 행동을 설계서 형태로 완성합니다.
            </p>
          </div>
          <div className="space-y-4 rounded-[36px] border border-slate-100 bg-slate-50/50 p-6 backdrop-blur-sm">
            <EvidenceRow label="AI 핵심 종합 진단" value="건축 환경 공학적 연결 고리는 명확하나, 심층 물리 수학적 모델링 근거 보완 필요." />
            <EvidenceRow label="문장 증명 소스" value="2학년 기하 세특 및 물리 II 탐구 활동에서 실질 수식 설계 기록 추적됨." />
            <EvidenceRow label="분석 신뢰 강도" value="높음 (Gemini 1.5 Pro 학생부 교차 검증 정확도 97.4%)" />
            <EvidenceRow label="추천 보완 액션" value="구조역학적 하중 분산 탐구를 위한 함수 모델 초안 워크숍 기획" />
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="relative z-10 mx-auto max-w-7xl px-6 py-24 lg:px-8">
        <div className="mx-auto max-w-3xl text-center space-y-4">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-purple-50 px-3 py-1 text-[10px] font-black text-purple-600 uppercase tracking-wider">TRANSPARENT PRICING</span>
          <h2 className="text-3xl font-black tracking-tight sm:text-4xl text-slate-900">결제 직후 소지하게 되는 결과물</h2>
          <p className="text-sm sm:text-base font-bold text-slate-500 max-w-xl mx-auto">
            추상적인 단어로 가격을 수식하지 않습니다. 상세 PDF 진단서, 개별 세특 보완 계획서, 보고서 워크숍 가이드라인 등 소장할 산출물을 기준으로 투명하게 정의합니다.
          </p>
        </div>
        <PricingSection />
      </section>

    </div>
  );
}

function EvidenceReportPreview() {
  return (
    <div className="mx-auto max-w-[580px] rounded-[36px] border border-slate-100 bg-white p-6 shadow-[0_35px_90px_-30px_rgba(99,102,241,0.18)] relative overflow-hidden">
      
      {/* 🚀 실시간 레이저 스캐닝 빔 애니메이션 */}
      <motion.div 
        animate={{ top: ['0%', '100%', '0%'] }} 
        transition={{ repeat: Infinity, duration: 3.5, ease: 'linear' }}
        className="absolute left-0 right-0 h-[3px] bg-gradient-to-r from-transparent via-indigo-500 to-transparent shadow-[0_0_15px_#6366f1] z-20 pointer-events-none" 
      />

      <div className="rounded-3xl bg-slate-950 p-6 text-white relative overflow-hidden shadow-2xl">
        {/* 다크 그라데이션 광배 */}
        <div className="absolute top-0 right-0 h-40 w-40 rounded-full bg-indigo-600/20 blur-2xl pointer-events-none" />

        <div className="flex items-start justify-between gap-4">
          <div>
            <span className="text-[10px] font-black uppercase tracking-[0.18em] text-indigo-400">STUDENT DATA SCANNER</span>
            <h3 className="mt-1 text-xl font-black">진단 → 보완 설계 → 워크숍 실행</h3>
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 backdrop-blur-md">
            <FileSearch className="text-indigo-400 animate-pulse" size={20} />
          </div>
        </div>

        <div className="mt-6 space-y-4">
          {[
            ['전공 적합성 지표', '최우수 (학문 융합 우수)', 'bg-gradient-to-r from-emerald-400 to-teal-400', '92%'],
            ['탐구 심화 스펙트럼', '보완 필요 (세부 수식 부재)', 'bg-gradient-to-r from-amber-400 to-orange-400', '58%'],
            ['구술 면접 설명 신뢰도', '보완 권장 (리스크 관리)', 'bg-gradient-to-r from-sky-400 to-blue-400', '72%'],
          ].map(([label, value, gradient, width]) => (
            <div key={label} className="rounded-2xl bg-white/[0.06] border border-white/[0.04] p-4 hover:bg-white/[0.08] transition-colors">
              <div className="flex items-center justify-between text-xs sm:text-sm font-black">
                <span className="text-slate-300">{label}</span>
                <span className="text-white">{value}</span>
              </div>
              <div className="mt-3.5 h-1.5 rounded-full bg-white/10 overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width }}
                  transition={{ duration: 1.2, ease: 'easeOut' }}
                  className={cn('h-full rounded-full', gradient)} 
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-6 space-y-3 relative z-10">
        <PreviewLine icon={ClipboardCheck} title="발견된 공백 지점" copy="수학적 미적분 모델링 기반의 물리 모델 수식 검증 기록 부재." />
        <PreviewLine icon={BookOpenCheck} title="추천 보완 주제" copy="기하 벡터를 이용한 구조역학 아치교량 하중 분산 모델링 설계" />
        <PreviewLine icon={MessageSquareText} title="보완 워크숍 초안" copy="보고서 초안 작성 및 20문항의 연계 면접 시뮬레이션 즉각 가동" />
      </div>
    </div>
  );
}

function WorkflowSection() {
  return (
    <section className="relative z-10 mx-auto max-w-7xl px-6 py-20 lg:px-8">
      <div className="mb-12 flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-[10px] font-black text-indigo-600 uppercase tracking-wider">CORE SYSTEM</span>
          <h2 className="mt-4 text-3xl font-black tracking-tight sm:text-4xl text-slate-900">물 흐르듯 매끄러운 단일 스캔 시스템</h2>
        </div>
        <p className="max-w-xl text-xs sm:text-sm font-bold leading-relaxed text-slate-400">
          복잡한 절차 없이 학생부 원본 PDF 업로드부터 공백 지점 분석, 주제 도출, 그리고 최종 보고서 초안 완성 및 워크숍 편집까지 막힘없이 한 번에 이어집니다.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {workflowSteps.map((step, index) => (
          <motion.div 
            key={step.title} 
            whileHover={{ y: -6, boxShadow: '0 20px 40px -15px rgba(99,102,241,0.12)' }}
            transition={{ duration: 0.25 }}
            className="rounded-3xl border border-slate-100 bg-white p-5.5 relative group cursor-pointer"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 text-xs font-black group-hover:bg-indigo-600 group-hover:text-white transition-all duration-300 shadow-sm">
              0{index + 1}
            </div>
            <h3 className="mt-5 text-base font-black text-slate-900 group-hover:text-indigo-600 transition-colors">{step.title}</h3>
            <p className="mt-2.5 text-xs font-bold leading-relaxed text-slate-400">{step.copy}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function EvidenceRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-4.5 hover:shadow-md transition-shadow">
      <p className="text-[10px] font-black text-slate-400 uppercase tracking-wider">{label}</p>
      <p className="mt-1.5 text-xs sm:text-sm font-bold leading-relaxed text-slate-800">{value}</p>
    </div>
  );
}

function PreviewLine({
  icon: Icon,
  title,
  copy,
}: {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  copy: string;
}) {
  return (
    <div className="flex gap-4.5 rounded-2xl border border-slate-100 bg-slate-50/50 p-4.5 backdrop-blur-sm">
      <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 shrink-0">
        <Icon size={16} />
      </div>
      <div>
        <h4 className="text-sm font-black text-slate-900">{title}</h4>
        <p className="mt-1 text-xs font-bold leading-relaxed text-slate-400">{copy}</p>
      </div>
    </div>
  );
}

function PricingSection() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="mt-14 grid gap-8 lg:grid-cols-3">
      {pricingPlans.map((plan) => (
        <motion.div
          key={plan.name}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className={cn(
            'flex flex-col rounded-[36px] border bg-white p-8 relative overflow-hidden transition-all duration-300 hover:shadow-xl hover:shadow-indigo-50 hover:-translate-y-1',
            plan.featured ? 'border-indigo-500 shadow-lg shadow-indigo-50' : 'border-slate-100',
          )}
        >
          {plan.featured && (
            <>
              {/* 무지갯빛 오라 가드 */}
              <div className="absolute top-0 inset-x-0 h-1.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-sky-400" />
              <span className="mb-5 inline-flex w-fit rounded-full bg-indigo-600 px-3.5 py-1 text-[10px] font-black text-white uppercase tracking-wider">
                가장 추천하는 에디션
              </span>
            </>
          )}
          <h3 className="text-2xl font-black text-slate-950">{plan.name}</h3>
          <p className="mt-2.5 text-xs font-bold leading-relaxed text-slate-400">{plan.description}</p>
          <p className="mt-8 text-4xl font-black tracking-tight text-slate-950">{plan.price}</p>
          <ul className="mt-8 flex-1 space-y-4">
            {plan.outputs.map((output) => (
              <li key={output} className="flex gap-3 text-xs sm:text-sm font-bold leading-relaxed text-slate-600">
                <Check size={16} className="mt-0.5 shrink-0 text-emerald-600" />
                {output}
              </li>
            ))}
          </ul>
          <Link
            to={isAuthenticated ? '/app/diagnosis' : plan.href}
            className={cn(
              'mt-9 inline-flex items-center justify-center gap-2 rounded-2xl py-4 text-sm font-black transition-all duration-300',
              plan.featured 
                ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md shadow-indigo-100 hover:shadow-indigo-200' 
                : 'bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900 border border-slate-100',
            )}
          >
            {plan.cta}
            <ArrowRight size={15} />
          </Link>
        </motion.div>
      ))}
    </div>
  );
}

const cn = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(' ');
