import React from 'react';
import { motion } from 'motion/react';
import { FileUp, Plus, Settings2 } from 'lucide-react';
import { SectionCard, SecondaryButton, WorkflowNotice } from '../primitives';

interface DiagnosisUploadProps {
  getRootProps: any;
  getInputProps: any;
  isDragActive: boolean;
  isUploading: boolean;
  handleOpenFileDialog: () => void;
  handleDropzoneKeyDown: (e: React.KeyboardEvent<HTMLDivElement>) => void;
  setStep: (step: any) => void;
  flowError: string | null;
}

export const DiagnosisUpload: React.FC<DiagnosisUploadProps> = ({
  getRootProps,
  getInputProps,
  isDragActive,
  isUploading,
  handleOpenFileDialog,
  handleDropzoneKeyDown,
  setStep,
  flowError,
}) => {
  return (
    <motion.div
      key="upload"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
    >
      <SectionCard
        title="생활기록부 PDF 등록"
        description="생기부 1개(최대 50MB)를 등록하시면 개인정보 보호 처리 후 AI가 꼼꼼히 읽어봅니다."
        className="overflow-hidden border-none bg-white/60 shadow-xl backdrop-blur-2xl ring-1 ring-white/50"
        actions={
          <SecondaryButton
            size="sm"
            onClick={() => setStep('GOALS')}
            className="bg-white/50 border-white/50 backdrop-blur-sm"
          >
            <Settings2 size={14} className="mr-1.5" />
            목표 대학 수정
          </SecondaryButton>
        }
      >
        <div className="grid gap-3 rounded-2xl bg-blue-50/50 p-6 sm:grid-cols-3 ring-1 ring-blue-100">
          <div className="flex flex-col gap-1 items-center text-center">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#004aad] text-xs font-bold text-white shadow-lg shadow-blue-500/20">
              1
            </div>
            <p className="text-sm font-black text-slate-800">기록 등록</p>
          </div>
          <div className="flex flex-col gap-1 items-center text-center">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-xs font-bold text-slate-500">
              2
            </div>
            <p className="text-sm font-bold text-slate-400">정밀 분석</p>
          </div>
          <div className="flex flex-col gap-1 items-center text-center">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-xs font-bold text-slate-500">
              3
            </div>
            <p className="text-sm font-bold text-slate-400">결과 확인</p>
          </div>
        </div>

        <div
          {...getRootProps({
            onClick: handleOpenFileDialog,
            onKeyDown: handleDropzoneKeyDown,
          })}
          className={`group relative mt-6 cursor-pointer overflow-hidden rounded-[2rem] border-2 border-dashed transition-all duration-300 ${
            isDragActive
              ? 'border-[#004aad] bg-[#004aad]/5 scale-[0.99]'
              : 'border-slate-200 bg-white hover:border-[#004aad]/40 hover:shadow-2xl hover:shadow-blue-500/10'
          } ${isUploading ? 'pointer-events-none opacity-60' : ''}`}
        >
          <input data-testid="diagnosis-upload-input" {...getInputProps()} />

          <div className="flex flex-col items-center px-6 py-12 text-center sm:py-20">
            <div className="relative mb-8">
              <div className="absolute inset-0 animate-ping rounded-full bg-blue-400 opacity-20"></div>
              <div className="relative flex h-24 w-24 items-center justify-center rounded-3xl bg-gradient-to-br from-[#004aad] to-[#0070f3] text-white shadow-lg shadow-blue-500/20">
                {isUploading ? (
                  <div className="w-12">
                    <div className="h-2 overflow-hidden rounded-full bg-white/20">
                      <motion.div
                        className="h-full rounded-full bg-white"
                        animate={{ x: ['-100%', '100%'] }}
                        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                      />
                    </div>
                  </div>
                ) : (
                  <FileUp size={42} className="transition-transform duration-300 group-hover:-translate-y-1" />
                )}
              </div>
            </div>

            <h3 className="text-2xl font-black tracking-tight text-slate-900 sm:text-3xl">
              생활기록부를 <span className="text-[#004aad]">이곳에 놓아주세요</span>
            </h3>
            <p className="mt-4 max-w-md text-lg font-medium text-slate-500 leading-relaxed">
              파일을 드래그하거나 버튼을 클릭하여 업로드하면 <br className="hidden sm:block" />
              즉시 AI 맞춤 진단이 시작됩니다.
            </p>

            <button
              type="button"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                handleOpenFileDialog();
              }}
              disabled={isUploading}
              className="mt-10 flex items-center gap-3 rounded-2xl bg-slate-900 px-8 py-4 text-base font-bold text-white shadow-xl shadow-slate-200 ring-offset-2 transition-all hover:bg-slate-800 hover:ring-2 hover:ring-slate-900 active:scale-95 disabled:opacity-50"
            >
              <Plus size={20} />
              컴퓨터에서 파일 찾기
            </button>
          </div>
        </div>

        {flowError ? (
          <div className="mt-6">
            <WorkflowNotice tone="danger" title="작업 중 오류 발생" description={flowError} />
          </div>
        ) : null}
      </SectionCard>
    </motion.div>
  );
};
