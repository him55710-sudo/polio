import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BookOpen, CheckCircle2, FileSearch, PenTool, ShieldCheck, Target } from 'lucide-react';
import { FaqAccordion } from '../components/FaqAccordion';
import { faqPreviewItems } from '../content/faq';
import { useAuth } from '../contexts/AuthContext';
import { buttonClassName } from '../components/ui';
import { cn } from '../lib/cn';

const workflowItems = [
  {
    title: '1. 목표 설정',
    description: '지원 대학과 학과를 설정해 분석 기준을 분명히 만듭니다.',
  },
  {
    title: '2. 기록 업로드',
    description: '학생부 PDF를 업로드하면 마스킹과 파싱이 자동으로 진행됩니다.',
  },
  {
    title: '3. 진단 실행',
    description: '강점, 보완 포인트, 위험 신호를 근거 기반으로 확인합니다.',
  },
  {
    title: '4. 워크숍 작성',
    description: '진단 결과를 바탕으로 초안을 작성하고 개선합니다.',
  },
];

const trustPoints = [
  '학생 작성 내용을 중심으로 유지합니다.',
  'AI 제안은 사용자 승인 후에만 문서에 반영됩니다.',
  '근거 문장을 확인할 수 있는 진단 구조를 제공합니다.',
];

export function Landing() {
  const { isAuthenticated } = useAuth();
  const startHref = isAuthenticated ? '/app' : '/auth';
  const startLabel = isAuthenticated ? '앱으로 이동' : '무료로 시작하기';

  return (
    <div className="bg-slate-50">
      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-16 text-center sm:px-6 lg:px-8 lg:py-20">
          <p className="mx-auto text-xs font-bold uppercase tracking-[0.18em] text-blue-600">학생부 기반 워크플로</p>
          <h1 className="mx-auto mt-4 max-w-4xl text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
            과장된 문구 대신
            <br />
            실제 준비 흐름을 제공합니다.
          </h1>
          <p className="mx-auto mt-6 max-w-3xl text-sm font-medium leading-8 text-slate-600">
            Uni Folia는 기록 업로드부터 진단, 워크숍 작성까지 이어지는 준비 워크플로를 제공합니다.
            화려한 대시보드보다 현재 상태와 다음 행동을 명확히 보여주는 데 집중합니다.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to={startHref} className={cn(buttonClassName({ variant: 'primary', size: 'lg' }), "rounded-2xl shadow-lg shadow-blue-500/20 px-8")}>
              지금 시작하기
              <ArrowRight size={18} />
            </Link>
            <Link to="/contact" className={cn(buttonClassName({ variant: 'secondary', size: 'lg' }), "rounded-2xl")}>
              문의하기
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid gap-4 lg:grid-cols-4">
          {workflowItems.map(item => (
            <article key={item.title} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-base font-bold text-slate-900">{item.title}</h2>
              <p className="mt-2 text-sm font-medium leading-6 text-slate-600">{item.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-slate-200 bg-white">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-14 sm:px-6 lg:grid-cols-2 lg:px-8">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">핵심 기능</p>
            <div className="mt-4 space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="inline-flex items-center gap-2 text-sm font-bold text-slate-800">
                  <Target size={16} className="text-blue-700" />
                  목표 중심 진단
                </p>
                <p className="mt-2 text-sm font-medium leading-6 text-slate-600">지원 목표에 맞춰 분석 기준을 자동 조정합니다.</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="inline-flex items-center gap-2 text-sm font-bold text-slate-800">
                  <FileSearch size={16} className="text-blue-700" />
                  근거 기반 결과
                </p>
                <p className="mt-2 text-sm font-medium leading-6 text-slate-600">진단 문장에 연결된 근거를 함께 확인할 수 있습니다.</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="inline-flex items-center gap-2 text-sm font-bold text-slate-800">
                  <PenTool size={16} className="text-blue-700" />
                  워크숍 중심 작성
                </p>
                <p className="mt-2 text-sm font-medium leading-6 text-slate-600">AI 제안을 검토한 뒤 사용자 의사로만 반영합니다.</p>
              </div>
            </div>
          </div>

          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">신뢰 원칙</p>
            <div className="mt-4 space-y-3">
              {trustPoints.map(point => (
                <div key={point} className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <CheckCircle2 size={16} className="mt-1 text-emerald-600" />
                  <p className="text-sm font-medium leading-6 text-slate-700">{point}</p>
                </div>
              ))}
              <div className="flex items-start gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4">
                <ShieldCheck size={16} className="mt-1 text-blue-700" />
                <p className="text-sm font-medium leading-6 text-blue-900">
                  Uni Folia는 준비 과정의 품질을 지원하는 도구이며, 입시 결과를 보장하지 않습니다.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">도움말</p>
            <h2 className="mt-2 text-2xl font-extrabold tracking-tight text-slate-900">자주 묻는 질문</h2>
          </div>
          <Link to="/faq" className="inline-flex items-center gap-2 rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700">
            전체 보기
            <ArrowRight size={14} />
          </Link>
        </div>
        <div className="mt-6">
          <FaqAccordion items={faqPreviewItems} initialOpenId={faqPreviewItems[0]?.id} compact />
        </div>
      </section>

      <section className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
          <div className="rounded-2xl border border-slate-200 bg-slate-900 p-8 text-center text-white lg:p-12">
            <p className="mx-auto text-xs font-bold uppercase tracking-[0.18em] text-blue-300">시작하기</p>
            <h2 className="mx-auto mt-3 text-2xl font-extrabold tracking-tight sm:text-3xl">지금 준비 흐름을 시작해 보세요.</h2>
            <p className="mx-auto mt-4 max-w-2xl text-sm font-medium leading-7 text-slate-300">
              학생은 바로 워크플로를 시작할 수 있고, 기관/제휴 문의는 별도 채널에서 진행할 수 있습니다.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-4">
              <Link to={startHref} className={cn(buttonClassName({ variant: 'primary', size: 'lg' }), "rounded-2xl px-10 shadow-xl shadow-blue-500/20")}>
                <BookOpen size={18} />
                준비 시작하기
              </Link>
              <Link to="/contact?type=partnership" className={cn(buttonClassName({ variant: 'ghost', size: 'lg' }), "rounded-2xl border border-white/20 px-10 text-white hover:bg-white/10")}>
                제휴 문의
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
