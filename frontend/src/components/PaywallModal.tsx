import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Lock, Check, X, Sparkles, CreditCard, Calendar } from 'lucide-react';
import { cn } from '../lib/cn';

interface PaywallModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type BillingCycle = 'monthly' | 'semester';

export function PaywallModal({ isOpen, onClose }: PaywallModalProps) {
  const [billingCycle, setBillingCycle] = useState<BillingCycle>('semester');

  if (!isOpen) return null;

  const handlePayment = (plan: string, price: number) => {
    // TODO: 토스페이먼츠 연동
    console.log(`Processing payment for ${plan} plan via Toss Payments. Amount: ${price}`);
    alert(`토스페이먼츠 연동 준비 중입니다.\n선택한 플랜: ${plan}\n결제 금액: ₩${price.toLocaleString()}`);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="w-full max-w-6xl bg-white rounded-3xl overflow-hidden shadow-2xl relative flex flex-col max-h-[95vh]"
      >
        <button onClick={onClose} className="absolute top-4 right-4 z-20 p-2 text-slate-400 hover:text-slate-600 bg-slate-100 rounded-full transition-colors">
          <X size={20} />
        </button>

        <div className="p-6 md:p-16 overflow-y-auto hide-scrollbar">
          <div className="text-center mb-16">
            <div className="inline-flex items-center justify-center p-4 bg-blue-50 text-blue-600 rounded-[1.5rem] mb-6">
              <Sparkles size={32} />
            </div>
            <h2 className="text-3xl md:text-5xl font-black text-slate-900 mb-4 md:mb-6 tracking-tight leading-tight">
              입시 준비의 새로운 기준,<br /><span className="text-blue-600">Uni Foli</span>
            </h2>
            <p className="text-slate-500 font-bold text-lg md:text-xl max-w-2xl mx-auto leading-relaxed px-2">
              학생부 분석부터 탐구 주제 추천, 모의 면접까지 완벽하게.<br className="hidden sm:block" />나에게 맞는 플랜을 선택하세요.
            </p>

            {/* Billing Toggle */}
            <div className="flex items-center justify-center mt-10 md:mt-12">
              <div className="bg-[#f2f4f6] p-1.5 rounded-[1.25rem] inline-flex relative border border-[#e5e8eb] shadow-inner w-full max-w-[340px]">
                <button
                  onClick={() => setBillingCycle('monthly')}
                  className={cn(
                    "relative z-10 flex-1 px-4 md:px-10 py-3 rounded-[1rem] font-black text-[15px] md:text-[16px] transition-all duration-300",
                    billingCycle === 'monthly' ? "text-[#191f28]" : "text-[#8b95a1] hover:text-[#4e5968]"
                  )}
                >
                  월간 결제
                </button>
                <button
                  onClick={() => setBillingCycle('semester')}
                  className={cn(
                    "relative z-10 flex-1 px-4 md:px-10 py-3 rounded-[1rem] font-black text-[15px] md:text-[16px] transition-all duration-300",
                    billingCycle === 'semester' ? "text-[#3182f6]" : "text-[#8b95a1] hover:text-[#4e5968]"
                  )}
                >
                  학기 결제
                </button>
                {/* Active Indicator */}
                <div
                  className="absolute inset-y-1.5 bg-white rounded-[1rem] shadow-[0_2px_8px_rgba(0,0,0,0.08)] transition-all duration-400 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
                  style={{
                    left: billingCycle === 'monthly' ? '6px' : 'calc(50% + 3px)',
                    width: 'calc(50% - 9px)'
                  }}
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8 max-w-6xl mx-auto relative z-10 items-stretch">
            {/* Free Plan */}
            <div className="bg-white border border-slate-200 rounded-[2rem] md:rounded-[2.5rem] p-6 md:p-10 flex flex-col shadow-sm hover:shadow-md transition-shadow">
              <h3 className="text-2xl font-black text-slate-800 mb-2">Free</h3>
              <p className="text-slate-500 text-base mb-8 font-bold h-12 leading-relaxed">가볍게 기능을 체험해보고 싶은 학생을 위한 플랜</p>
              <div className="mb-6 md:mb-8 h-16 md:h-20 flex flex-col justify-end">
                <div className="h-6" />
                <div className="text-3xl md:text-4xl font-black text-slate-900 flex items-baseline gap-1">
                  ₩0
                  <span className="text-sm md:text-lg text-slate-400 font-medium">/{billingCycle === 'monthly' ? '월' : '학기'}</span>
                </div>
              </div>
              <ul className="space-y-4 mb-8 flex-1">
                <li className="flex items-start gap-3 text-slate-600 font-medium text-sm">
                  <Check size={18} className="text-slate-400 shrink-0 mt-0.5" />
                  기본 AI 대화 및 아이디어 스케치
                </li>
                <li className="flex items-start gap-3 text-slate-600 font-medium text-sm">
                  <Check size={18} className="text-slate-400 shrink-0 mt-0.5" />
                  월 5회 생기부 진단
                </li>
                <li className="flex items-start gap-3 text-slate-600 font-medium text-sm">
                  <Check size={18} className="text-slate-400 shrink-0 mt-0.5" />
                  워터마크가 포함된 PDF 다운로드
                </li>
              </ul>
              <button onClick={onClose} className="w-full py-3.5 rounded-2xl font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors">
                현재 플랜 유지
              </button>
            </div>

            {/* Pro Plan */}
            <div className="bg-white border-2 border-[#3182f6] rounded-[2rem] md:rounded-[2.5rem] p-6 md:p-10 flex flex-col shadow-2xl relative transform md:-translate-y-4 z-20">
              <div className="absolute top-0 inset-x-0 flex justify-center -translate-y-1/2">
                <div className="bg-[#3182f6] text-white text-xs font-black px-6 py-2.5 rounded-full shadow-lg uppercase tracking-wider">
                  가장 인기있는 플랜
                </div>
              </div>
              <h3 className="text-2xl font-black text-[#3182f6] mb-2">Pro</h3>
              <p className="text-slate-500 text-base mb-8 font-bold h-12 leading-relaxed">입시 준비 시간을 획기적으로 단축하고 싶은 학생</p>
              
              <div className="mb-6 md:mb-8 h-16 md:h-20 flex flex-col justify-end">
                <div className="h-6">
                  {billingCycle === 'semester' && (
                    <span className="text-slate-400 line-through text-xs md:text-sm font-bold mb-0.5 opacity-60">₩35,400</span>
                  )}
                </div>
                <div className="text-3xl md:text-4xl font-black text-slate-900 flex items-baseline gap-1">
                  ₩{billingCycle === 'monthly' ? '5,900' : '23,900'}
                  <span className="text-sm md:text-lg text-slate-400 font-medium">/{billingCycle === 'monthly' ? '월' : '학기'}</span>
                </div>
              </div>

              <ul className="space-y-5 mb-10 flex-1">
                <li className="flex items-start gap-4 text-slate-800 font-bold text-sm leading-tight">
                  <Check size={20} className="text-[#3182f6] shrink-0 mt-0.5" />
                  무제한 생기부 심층 진단
                </li>
                <li className="flex items-start gap-4 text-slate-800 font-bold text-sm leading-tight">
                  <Check size={20} className="text-[#3182f6] shrink-0 mt-0.5" />
                  워터마크 없는 깔끔한 PDF 제공
                </li>
                <li className="flex items-start gap-4 text-slate-800 font-bold text-sm leading-tight">
                  <Check size={20} className="text-[#3182f6] shrink-0 mt-0.5" />
                  HWPX 절대 조판 무제한 다운
                </li>
              </ul>
              <button
                onClick={() => handlePayment('Pro', billingCycle === 'monthly' ? 5900 : 23900)}
                className="w-full py-4.5 rounded-[1.25rem] font-black text-white bg-[#3182f6] hover:bg-[#1b64da] transition-all active:scale-[0.98] shadow-lg shadow-blue-100 flex items-center justify-center gap-2"
              >
                <CreditCard size={20} />
                Pro 플랜 시작하기
              </button>
            </div>

            {/* Ultra Plan */}
            <div className="bg-[#191f28] border border-slate-700 rounded-[2rem] md:rounded-[2.5rem] p-6 md:p-10 flex flex-col shadow-xl">
              <h3 className="text-2xl font-black text-blue-400 mb-2">Ultra</h3>
              <p className="text-slate-400 text-base mb-8 font-bold h-12 leading-relaxed">압도적인 퀄리티로 최상위권을 노리는 학생</p>
              
              <div className="mb-6 md:mb-8 h-16 md:h-20 flex flex-col justify-end">
                <div className="h-6">
                  {billingCycle === 'semester' && (
                    <span className="text-slate-600 line-through text-xs md:text-sm font-bold mb-0.5 opacity-60">₩59,400</span>
                  )}
                </div>
                <div className="text-3xl md:text-4xl font-black text-white flex items-baseline gap-1">
                  ₩{billingCycle === 'monthly' ? '9,900' : '39,900'}
                  <span className="text-sm md:text-lg text-slate-500 font-medium">/{billingCycle === 'monthly' ? '월' : '학기'}</span>
                </div>
              </div>

              <ul className="space-y-5 mb-10 flex-1">
                <li className="flex items-start gap-4 text-slate-300 font-bold text-sm leading-tight">
                  <Check size={20} className="text-blue-400 shrink-0 mt-0.5" />
                  Pro 모든 기능 포함
                </li>
                <li className="flex items-start gap-4 text-slate-300 font-bold text-sm leading-tight">
                  <Check size={20} className="text-blue-400 shrink-0 mt-0.5" />
                  AI 실전 모의 면접 무제한
                </li>
                <li className="flex items-start gap-4 text-slate-300 font-bold text-sm leading-tight">
                  <Check size={20} className="text-blue-400 shrink-0 mt-0.5" />
                  최우선 응답 속도 지원
                </li>
              </ul>
              <button
                onClick={() => handlePayment('Ultra', billingCycle === 'monthly' ? 9900 : 39900)}
                className="w-full py-4.5 rounded-[1.25rem] font-black text-white bg-blue-600 hover:bg-blue-700 transition-all active:scale-[0.98] shadow-lg shadow-blue-900/40 flex items-center justify-center gap-2"
              >
                <Sparkles size={20} />
                Ultra 플랜 시작하기
              </button>
            </div>
          </div>
          
          <div className="mt-16 pb-8 text-center text-sm font-bold text-slate-400 flex items-center justify-center gap-3">
            <Lock size={16} /> 토스페이먼츠를 통한 안전한 결제를 지원합니다.
          </div>
        </div>
      </motion.div>
    </div>
  );
}

