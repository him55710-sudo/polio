import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import {
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  FileText,
  GraduationCap,
  MessageSquareText,
  Search,
  Sparkles,
  Star,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const quickServices = [
  {
    title: 'AI 생기부 진단',
    copy: '기록의 강점과 공백을 전공 근거 중심으로 정리',
    icon: ClipboardCheck,
    color: 'bg-[#ffdf55] text-[#1f2a44]',
  },
  {
    title: '세특 카드',
    copy: '과목별 문장 근거를 탐구 소재로 변환',
    icon: BookOpenCheck,
    color: 'bg-[#e9f3ff] text-[#1656b8]',
  },
  {
    title: '탐구보고서',
    copy: '주제 선정부터 보고서 초안까지 이어서 작성',
    icon: FileText,
    color: 'bg-[#f0f6ed] text-[#287947]',
  },
  {
    title: '면접 TALK',
    copy: '내 기록에서 나올 질문을 대화형으로 대비',
    icon: MessageSquareText,
    color: 'bg-[#fff1e7] text-[#c5541b]',
  },
];

const topicRows = [
  ['#건축공학', '#반도체', '#인공지능', '#의생명', '#기후테크', '#교육학'],
  ['#수학모델링', '#사회문제탐구', '#문헌분석', '#실험설계', '#진로활동', '#면접질문'],
];

const reportCards = [
  { category: '자연계열', title: '하중 분산을 함수 모델로 해석하는 구조역학 탐구', meta: '물리 · 수학 · 건축' },
  { category: '의생명', title: '세포 신호전달 오류와 질병 예측 모델 분석', meta: '생명과학 · 통계' },
  { category: '사회계열', title: '청소년 플랫폼 이용 패턴과 정보 격차 보고서', meta: '사회문화 · 데이터' },
];

const magazineCards = [
  { title: '학생부 문장에서 전공 근거를 찾는 법', label: '입시 매거진' },
  { title: '탐구 주제가 얕아 보일 때 보완하는 순서', label: '진로 정보' },
  { title: '면접에서 보고서 주제를 설명하는 구조', label: '리로TALK' },
];

export function LandingPortalVariant() {
  const { isAuthenticated } = useAuth();
  const startHref = isAuthenticated ? '/app/diagnosis' : '/auth';

  return (
    <div className="bg-[#f6f7fb] text-[#202632]">
      <section className="border-b border-[#e7ebf2] bg-white">
        <div className="mx-auto max-w-7xl px-5 py-12 lg:px-8 lg:py-16">
          <div className="grid gap-8 lg:grid-cols-[1fr_420px] lg:items-center">
            <motion.div
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.42 }}
              className="text-center lg:text-left"
            >
              <div className="mx-auto mb-5 inline-flex items-center gap-2 rounded-full border border-[#ffe889] bg-[#fff8d8] px-4 py-2 text-xs font-black text-[#7a5b00] lg:mx-0">
                <Sparkles size={15} />
                생기부 기반 AI 진로·진학 관리
              </div>
              <h1 className="text-4xl font-black leading-[1.12] tracking-tight text-[#151b2d] sm:text-6xl">
                나의 기록을 읽고
                <span className="block text-[#1754c8]">탐구·세특·면접까지 연결</span>
              </h1>
              <p className="mx-auto mt-5 max-w-2xl text-base font-semibold leading-8 text-[#586174] lg:mx-0">
                UniFoli는 학생부 PDF를 분석해 전공 연결 근거, 보완 탐구, 보고서 초안, 면접 질문을 한 흐름으로 정리합니다.
              </p>
              <div className="mx-auto mt-8 flex max-w-xl flex-col gap-3 rounded-lg border border-[#dfe5ee] bg-white p-2 shadow-sm sm:flex-row lg:mx-0">
                <div className="flex flex-1 items-center gap-2 px-3 py-2 text-left">
                  <Search size={18} className="text-[#1754c8]" />
                  <span className="text-sm font-bold text-[#747d90]">생기부 PDF 또는 목표 전공으로 시작</span>
                </div>
                <Link
                  to={startHref}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#ffdc3e] px-5 py-3 text-sm font-black text-[#1d2435] transition hover:bg-[#ffd11f]"
                >
                  진단 시작
                  <ArrowRight size={17} />
                </Link>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.48, delay: 0.08 }}
              className="overflow-hidden rounded-lg border border-[#e5eaf2] bg-[#fff9dd] shadow-[0_24px_60px_rgba(29,36,53,0.12)]"
            >
              <div className="border-b border-[#f0dc77] bg-[#ffdf55] px-5 py-4">
                <p className="text-xs font-black uppercase tracking-[0.16em] text-[#715400]">UniFoli membership+</p>
                <h2 className="mt-1 text-2xl font-black text-[#1d2435]">기록 분석 리포트</h2>
              </div>
              <div className="grid gap-0 sm:grid-cols-[1fr_150px]">
                <div className="space-y-3 bg-white p-5">
                  {[
                    ['전공 연결성', '근거 충분', '78%'],
                    ['탐구 심화', '보완 필요', '54%'],
                    ['면접 설명력', '질문 생성', '69%'],
                  ].map(([label, value, width]) => (
                    <div key={label} className="rounded-lg border border-[#edf1f6] bg-[#f8fafc] p-4">
                      <div className="flex items-center justify-between text-sm font-black">
                        <span>{label}</span>
                        <span className="text-[#1754c8]">{value}</span>
                      </div>
                      <div className="mt-3 h-2 rounded-full bg-[#e2e8f0]">
                        <div className="h-2 rounded-full bg-[#ffdf55]" style={{ width }} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex items-center justify-center bg-[#f5f7fb] px-6 py-8">
                  <img src="/logo-unifoli-mark.png" alt="UniFoli" className="h-32 w-32 rounded-lg object-contain shadow-sm" />
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-10 lg:px-8">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {quickServices.map(({ title, copy, icon: Icon, color }) => (
            <Link
              key={title}
              to={startHref}
              className="group rounded-lg border border-[#e5eaf2] bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-[#ffdf55]"
            >
              <span className={`inline-flex h-11 w-11 items-center justify-center rounded-lg ${color}`}>
                <Icon size={20} />
              </span>
              <h3 className="mt-4 text-lg font-black text-[#1f2637]">{title}</h3>
              <p className="mt-2 text-sm font-semibold leading-6 text-[#626b7d]">{copy}</p>
              <span className="mt-4 inline-flex items-center gap-1 text-sm font-black text-[#1754c8]">
                바로가기
                <ChevronRight size={16} className="transition group-hover:translate-x-1" />
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="border-y border-[#e5eaf2] bg-white py-14">
        <div className="mx-auto max-w-7xl px-5 lg:px-8">
          <div className="text-center">
            <p className="text-sm font-black uppercase tracking-[0.18em] text-[#1754c8]">AI 탐구주제</p>
            <h2 className="mt-3 text-3xl font-black tracking-tight text-[#151b2d] sm:text-4xl">내 기록에서 시작하는 탐구 키워드</h2>
          </div>
          <div className="mt-9 space-y-3 overflow-hidden">
            {topicRows.map((row, index) => (
              <div key={index} className="flex min-w-max gap-3">
                {row.concat(row).map((tag, tagIndex) => (
                  <span
                    key={`${tag}-${tagIndex}`}
                    className="rounded-full border border-[#fde58a] bg-[#fff8d8] px-5 py-3 text-sm font-black text-[#6e560b]"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-5 py-14 lg:grid-cols-[0.95fr_1.05fr] lg:px-8">
        <div className="rounded-lg border border-[#e5eaf2] bg-white p-6 shadow-sm">
          <p className="text-sm font-black uppercase tracking-[0.18em] text-[#1754c8]">생기부 진단</p>
          <h2 className="mt-3 text-3xl font-black tracking-tight text-[#151b2d]">근거, 공백, 다음 행동을 한 화면에서</h2>
          <p className="mt-4 text-sm font-semibold leading-7 text-[#626b7d]">
            학생부 문장을 그대로 근거로 삼아 전공 연결성과 보완 방향을 보여줍니다.
          </p>
          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            {['근거 추출', '보완 탐구', '면접 질문'].map((item) => (
              <div key={item} className="rounded-lg border border-[#edf1f6] bg-[#f8fafc] p-4">
                <CheckCircle2 size={18} className="text-[#287947]" />
                <p className="mt-3 text-sm font-black text-[#1f2637]">{item}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-4">
          {reportCards.map((card) => (
            <article key={card.title} className="rounded-lg border border-[#e5eaf2] bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="rounded-full bg-[#e9f3ff] px-3 py-1 text-xs font-black text-[#1754c8]">{card.category}</span>
                <span className="text-xs font-bold text-[#8b95a7]">{card.meta}</span>
              </div>
              <h3 className="mt-4 break-keep text-lg font-black leading-7 text-[#1f2637]">{card.title}</h3>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-[#e5eaf2] bg-white py-14">
        <div className="mx-auto max-w-7xl px-5 lg:px-8">
          <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.18em] text-[#1754c8]">리로TALK style</p>
              <h2 className="mt-3 text-3xl font-black tracking-tight text-[#151b2d]">입시 콘텐츠를 카드처럼 빠르게 확인</h2>
            </div>
            <Link to={startHref} className="inline-flex items-center gap-2 text-sm font-black text-[#1754c8]">
              전체 보기
              <ArrowRight size={16} />
            </Link>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {magazineCards.map((card, index) => (
              <article key={card.title} className="rounded-lg border border-[#e5eaf2] bg-[#f8fafc] p-5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black text-[#1754c8]">{card.label}</span>
                  <Star size={17} className={index === 0 ? 'fill-[#ffdf55] text-[#d59b00]' : 'text-[#9aa5b5]'} />
                </div>
                <h3 className="mt-8 min-h-16 break-keep text-xl font-black leading-7 text-[#1f2637]">{card.title}</h3>
                <p className="mt-4 text-sm font-semibold text-[#626b7d]">학생부와 연결되는 실행 중심 콘텐츠</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-14 lg:px-8">
        <div className="grid gap-5 rounded-lg border border-[#e5eaf2] bg-[#1f2a44] p-6 text-white sm:grid-cols-[1fr_auto] sm:items-center">
          <div>
            <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-lg bg-[#ffdf55] text-[#1f2a44]">
              <GraduationCap size={23} />
            </div>
            <h2 className="text-3xl font-black tracking-tight">기록을 올리면 다음 행동까지 바로 이어집니다</h2>
            <p className="mt-3 text-sm font-semibold leading-7 text-slate-200">
              진단 리포트, 탐구보고서, 면접 질문을 같은 작업 흐름 안에서 관리하세요.
            </p>
          </div>
          <Link
            to={startHref}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#ffdf55] px-6 py-4 text-sm font-black text-[#1f2a44] transition hover:bg-[#ffd11f]"
          >
            생기부 진단 시작
            <ArrowRight size={17} />
          </Link>
        </div>
      </section>
    </div>
  );
}
