import React, { useEffect } from 'react';
import { ErrorBoundary } from 'react-error-boundary';
import { RefreshCw, Compass, ArrowRight } from 'lucide-react';

function ErrorFallback({ error, resetErrorBoundary }: { error: any; resetErrorBoundary: () => void }) {
  useEffect(() => {
    // 1. ChunkLoadError 또는 동적 임포트 에러 판정
    const isChunkError =
      error?.name === 'ChunkLoadError' ||
      /ChunkLoadError/i.test(error?.message || '') ||
      /Failed to fetch dynamically imported module/i.test(error?.message || '') ||
      /Loading chunk/i.test(error?.message || '') ||
      /error loading dynamically imported module/i.test(error?.message || '');

    if (isChunkError) {
      const hasReloaded = sessionStorage.getItem('chunk-error-reload-timestamp');
      const now = Date.now();

      // 무한 루프 새로고침 차단용 락 설정 (최근 10초 이내인 경우에만 오류 화면 노출)
      if (!hasReloaded || now - parseInt(hasReloaded, 10) > 10000) {
        sessionStorage.setItem('chunk-error-reload-timestamp', String(now));
        window.location.reload();
        return;
      }
    }
  }, [error]);

  const handleHomeRedirect = () => {
    sessionStorage.removeItem('chunk-error-reload-timestamp');
    window.location.href = '/';
  };

  const handleReset = () => {
    sessionStorage.removeItem('chunk-error-reload-timestamp');
    resetErrorBoundary();
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4 sm:p-6 select-none font-sans">
      <div className="relative w-full max-w-md overflow-hidden rounded-[32px] border border-slate-100 bg-white p-6 sm:p-8 shadow-[0_24px_50px_-12px_rgba(15,23,42,0.06)] flex flex-col items-center text-center">
        {/* 상단 파란색 그라디언트 탑 데코 밴드 */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-blue-500 via-indigo-500 to-violet-500" />
        
        {/* 파스텔톤 우주 나침반 서클 일러스트 */}
        <div className="mt-4 mb-6 flex h-20 w-20 items-center justify-center rounded-[24px] bg-indigo-50/70 text-indigo-500 shadow-sm relative overflow-hidden">
          <div className="absolute inset-0 bg-indigo-100/30 rounded-full scale-75 blur-md animate-pulse" />
          <Compass size={36} className="relative z-10 text-indigo-500 animate-[spin_12s_linear_infinite]" strokeWidth={1.5} />
        </div>

        {/* 안도감을 제공하는 긍정형 카피라이팅 헤드라인 */}
        <h2 className="text-xl font-black tracking-tight text-slate-950 sm:text-2xl">
          서비스 환경이 개선되었습니다
        </h2>
        <p className="mt-3 text-xs font-bold leading-relaxed text-slate-500 sm:text-sm px-1">
          더 신속하고 안전한 연결을 위해 화면을 일시적으로 동기화하고 있습니다. 아래 버튼을 눌러 최신 환경을 바로 불러와 주세요.
        </p>

        {/* 흉측한 기술 오류 디테일 화면 노출 전면 영구 박멸! 콘솔 로깅으로 대체 */}
        {(() => {
          console.error('[Captured Dynamic Bundle Error]:', error);
          return null;
        })()}

        {/* 프리미엄 명품 복구 액션 그룹 */}
        <div className="mt-8 flex w-full flex-col gap-2">
          <button
            onClick={handleReset}
            className="flex w-full h-12 items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 text-sm font-black text-white shadow-md shadow-indigo-100 hover:opacity-95 active:scale-[0.98] transition-all"
          >
            <RefreshCw size={15} />
            새로고침 및 다시 연결
          </button>
          
          <button
            onClick={handleHomeRedirect}
            className="flex w-full h-12 items-center justify-center gap-1.5 rounded-2xl border border-slate-200 bg-white px-6 text-sm font-black text-slate-600 hover:bg-slate-50 active:scale-[0.98] transition-all"
          >
            홈 화면으로 안전하게 이동
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

export function GlobalErrorBoundary({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary
      FallbackComponent={ErrorFallback}
      onReset={() => {
        window.location.reload();
      }}
    >
      {children}
    </ErrorBoundary>
  );
}
