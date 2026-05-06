import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { FileUp, Loader2, Plus, Settings2, Trash2, CheckCircle2 } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';

import { useOnboardingStore } from '../../store/onboardingStore';
import { SectionCard, SurfaceCard } from '../primitives';
import { cn } from '../../lib/cn';
import { searchUniversities } from '../../lib/educationCatalog';
import { UniversityLogo } from '../UniversityLogo';

const SPECIAL_UNIVERSITIES = [
  '카이스트', 'KAIST', '한국과학기술원', 
  '유니스트', 'UNIST', '울산과학기술원', 
  '지스트', 'GIST', '광주과학기술원', 
  '디지스트', 'DGIST', '대구경북과학기술원', 
  '켄텍', 'KENTECH', '한국에너지공과대학교', 
  '한국예술종합학교', '한예종', 
  '경찰대학', '육군사관학교', '해군사관학교', '공군사관학교', '국군간호사관학교', '한국전통문화대학교'
];

export const isSpecialUniversity = (univName: string) => SPECIAL_UNIVERSITIES.some(su => univName.includes(su));
export const getRegularGoalCount = (univs: string[]) => univs.filter(u => !isSpecialUniversity(u)).length;

interface DiagnosisUnifiedSetupProps {
  onUploadStart: (file: File) => Promise<void>;
  isUploading: boolean;
  flowError: string | null;
}

interface GoalDraft {
  university: string;
  major: string;
}

function stripRankPrefix(value: string) {
  return value.trim().replace(/^\d+\s*[^:：]{0,8}[:：]\s*/, '').trim();
}

function parseInterestGoal(value: string): GoalDraft {
  const text = String(value || '').trim();
  const match = text.match(/^(.+)\s\((.+)\)$/);
  if (!match) return { university: text, major: '' };
  return {
    university: (match[1] || '').trim(),
    major: (match[2] || '').trim(),
  };
}

function formatInterestGoal(goal: GoalDraft) {
  return goal.major ? `${goal.university} (${goal.major})` : goal.university;
}

export const DiagnosisUnifiedSetup: React.FC<DiagnosisUnifiedSetupProps> = ({
  onUploadStart,
  isUploading,
  flowError,
}) => {
  const { profile, goals, goalList, setGoalList, setProfile, submitProfile, submitGoals } = useOnboardingStore();
  
  const [major1, setMajor1] = useState('');
  const [major2, setMajor2] = useState('');
  const [major3, setMajor3] = useState('');
  
  const [univInput, setUnivInput] = useState('');
  const [selectedUnivs, setSelectedUnivs] = useState<string[]>([]);
  
  // Hydrate from store if exists
  useEffect(() => {
    if (goalList.length > 0) {
      setSelectedUnivs(Array.from(new Set(goalList.map((goal) => goal.university).filter(Boolean))));
      const parts = goalList.map((goal) => goal.major).filter(Boolean);
      if (parts[0]) setMajor1(parts[0]);
      if (parts[1]) setMajor2(parts[1]);
      if (parts[2]) setMajor3(parts[2]);
      return;
    }

    if (goals.target_major) {
      const parts = goals.target_major.split(',').map(stripRankPrefix);
      if (parts[0]) setMajor1(parts[0]);
      if (parts[1]) setMajor2(parts[1]);
      if (parts[2]) setMajor3(parts[2]);
    }
    
    const univs: string[] = [];
    if (goals.target_university) univs.push(goals.target_university);
    if (goals.interest_universities) {
      goals.interest_universities.forEach(u => {
        const parsed = parseInterestGoal(u);
        if (parsed.university) univs.push(parsed.university);
      });
    }
    if (univs.length > 0) {
      setSelectedUnivs(Array.from(new Set(univs)));
    }
  }, [goalList, goals]);

  const handleAddUniv = (univ: string) => {
    if (selectedUnivs.includes(univ)) {
      toast.error('이미 추가된 대학입니다.');
      return;
    }
    
    const isSpecial = isSpecialUniversity(univ);
    const regularCount = getRegularGoalCount(selectedUnivs);
    
    if (!isSpecial && regularCount >= 6) {
      toast.error('일반 대학은 최대 6개까지만 선택할 수 있습니다. (특수대는 추가 가능)');
      return;
    }
    
    setSelectedUnivs(prev => [...prev, univ]);
    setUnivInput('');
  };

  const handleRemoveUniv = (univ: string) => {
    setSelectedUnivs(prev => prev.filter(u => u !== univ));
  };

  const buildSelectedGoals = (): GoalDraft[] => {
    const rankedMajors = [major1, major2, major3].map((major) => major.trim());
    return selectedUnivs.map((university, index) => ({
      university,
      major: rankedMajors[index] || rankedMajors[0] || '',
    }));
  };

  const selectedGoals = buildSelectedGoals();

  const handleDrop = async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    if (!profile.grade || !profile.track) {
      toast.error('학년과 계열을 선택해 주세요.');
      return;
    }
    if (!major1) {
      toast.error('최소한 1지망 학과는 입력해 주세요.');
      return;
    }
    if (selectedUnivs.length === 0) {
      toast.error('목표 대학을 최소 1개 이상 선택해 주세요.');
      return;
    }

    // Prepare Profile
    const profileOk = await submitProfile();
    if (!profileOk) return;

    // Prepare Goals
    const rankedGoals = buildSelectedGoals();
    const [primaryGoal, ...otherGoals] = rankedGoals;
    if (!primaryGoal) {
      toast.error('목표 대학을 최소 1개 이상 선택해 주세요.');
      return;
    }

    setGoalList(rankedGoals.map((goal, index) => ({
      id: index === 0 ? 'main' : `interest-${index - 1}`,
      university: goal.university,
      major: goal.major,
    })));

    const target_university = primaryGoal.university;
    const target_major = primaryGoal.major;
    const interest_universities = otherGoals.map(formatInterestGoal);

    const goalsOk = await submitGoals({
      target_university,
      target_major,
      admission_type: profile.grade === 'N수생' ? '정시' : '학생부종합',
      interest_universities
    });
    if (!goalsOk) return;

    // Trigger Upload
    await onUploadStart(file);
  };

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop: handleDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    disabled: isUploading,
    noClick: true,
  });

  const univPreviewName = univInput.trim();

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="w-full"
    >
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
        
        {/* Left Column: Configuration */}
        <div className="lg:col-span-5 flex flex-col">
          <SectionCard title="기본 설정" description="생기부 분석에 필요한 정보를 입력합니다." className="p-6 flex-1 flex flex-col justify-between">
            
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-500 mb-1 block">학년</label>
                  <select
                    value={profile.grade}
                    onChange={(e) => setProfile({ grade: e.target.value })}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm font-bold outline-none focus:border-indigo-600 focus:bg-white"
                  >
                    <option value="">선택</option>
                    <option value="고1">고1</option>
                    <option value="고2">고2</option>
                    <option value="고3">고3</option>
                    <option value="N수생">N수생</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-500 mb-1 block">계열</label>
                  <select
                    value={profile.track}
                    onChange={(e) => setProfile({ track: e.target.value })}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm font-bold outline-none focus:border-indigo-600 focus:bg-white"
                  >
                    <option value="">선택</option>
                    <option value="인문">인문</option>
                    <option value="자연">자연</option>
                    <option value="예체능">예체능</option>
                    <option value="기타">기타</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-500 mb-1 block">희망 학과 (1~3지망)</label>
                <div className="flex flex-col gap-2">
                  <input placeholder="1지망 (예: 컴퓨터공학과)" value={major1} onChange={e => setMajor1(e.target.value)} className="w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm font-bold outline-none focus:border-indigo-600 focus:bg-white" />
                  <input placeholder="2지망 (선택)" value={major2} onChange={e => setMajor2(e.target.value)} className="w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm font-bold outline-none focus:border-indigo-600 focus:bg-white" />
                  <input placeholder="3지망 (선택)" value={major3} onChange={e => setMajor3(e.target.value)} className="w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm font-bold outline-none focus:border-indigo-600 focus:bg-white" />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-end mb-1">
                  <label className="text-xs font-bold text-slate-500 block">목표 대학 (일반 6개 + 특수대)</label>
                  <span className="text-[10px] font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                    일반대 {getRegularGoalCount(selectedUnivs)}/6
                  </span>
                </div>
                <div className="relative mb-3">
                  <input
                    value={univInput}
                    onChange={(e) => setUnivInput(e.target.value)}
                    placeholder="대학명 검색 (예: 서울대학교)"
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 pr-10 text-sm font-bold outline-none focus:border-indigo-600 focus:bg-white"
                  />
                  {univPreviewName.length >= 2 && (
                    <UniversityLogo
                      universityName={univPreviewName}
                      className="pointer-events-none absolute right-2 top-1.5 h-6 w-6 rounded-md bg-white object-contain p-0.5 shadow-sm"
                    />
                  )}
                  {univInput && (
                    <div className="absolute left-0 right-0 top-full z-20 mt-1 max-h-48 overflow-auto rounded-xl border border-slate-200 bg-white p-1 shadow-xl">
                      {searchUniversities(univInput, { excludeNames: selectedUnivs }).map((suggestion) => (
                        <button
                          key={suggestion.label}
                          type="button"
                          onClick={() => handleAddUniv(suggestion.label)}
                          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left hover:bg-indigo-50"
                        >
                          <UniversityLogo universityName={suggestion.label} className="h-5 w-5 rounded bg-white object-contain" />
                          <span className="text-sm font-bold text-slate-700">{suggestion.label}</span>
                          {isSpecialUniversity(suggestion.label) && (
                            <span className="ml-auto text-[10px] font-bold text-purple-500 bg-purple-50 px-1.5 py-0.5 rounded-full">특수대</span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <AnimatePresence>
                    {selectedGoals.map((goal, idx) => (
                      <motion.div
                        key={goal.university}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.8 }}
                        className={cn(
                          "flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-bold shadow-sm border",
                          isSpecialUniversity(goal.university)
                            ? "border-purple-100 bg-purple-50 text-purple-700"
                            : idx === 0 
                              ? "border-indigo-200 bg-indigo-50 text-indigo-700" 
                              : "border-slate-200 bg-white text-slate-700"
                        )}
                      >
                        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white text-[11px] font-black shadow-sm">
                          {idx + 1}
                        </span>
                        <UniversityLogo universityName={goal.university} className="h-7 w-7 shrink-0 rounded-lg bg-white object-contain p-1" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-black">{goal.university}</p>
                          <p className="truncate text-[11px] font-bold opacity-70">{goal.major || '학과 미정'}</p>
                        </div>
                        {idx === 0 ? <CheckCircle2 size={14} className="shrink-0" /> : null}
                        <button onClick={() => handleRemoveUniv(goal.university)} className="ml-1 shrink-0 text-slate-400 hover:text-red-500">
                          <Trash2 size={12} />
                        </button>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                  {selectedUnivs.length === 0 && (
                    <span className="text-xs text-slate-400 italic">선택된 대학이 없습니다.</span>
                  )}
                </div>
              </div>

            </div>
          </SectionCard>
        </div>

        {/* Right Column: Upload */}
        <div className="lg:col-span-7 flex flex-col">
          <div
            {...getRootProps({ onClick: open })}
            className={cn(
              'relative flex flex-1 min-h-[480px] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-3xl border-2 border-dashed transition-all duration-300 p-6 sm:p-10 shadow-sm',
              isDragActive
                ? 'border-indigo-500 bg-indigo-50/40 scale-[0.99] shadow-inner ring-4 ring-indigo-100'
                : 'border-slate-200 bg-slate-50/10 hover:border-indigo-400 hover:bg-white hover:shadow-2xl hover:shadow-indigo-100/30',
              isUploading && 'pointer-events-none opacity-60'
            )}
          >
            <input data-testid="diagnosis-upload-input" {...getInputProps()} />
            
            <div className="relative mb-6">
              <div className="absolute inset-0 animate-ping rounded-2xl bg-indigo-250 opacity-20" />
              <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-lg shadow-indigo-200">
                {isUploading ? (
                  <Loader2 size={32} className="animate-spin" />
                ) : (
                  <FileUp size={32} strokeWidth={1.5} />
                )}
              </div>
            </div>

            <h2 className="text-2xl font-black text-slate-900 mb-4 text-center">
              {isUploading ? '분석 준비 중...' : isDragActive ? '파일을 여기에 놓으세요' : 'PDF 파일을 끌어오거나 클릭하여 업로드'}
            </h2>
            
            <div className="flex flex-wrap justify-center gap-3 mb-8">
               <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-4 py-1.5 text-sm font-bold text-slate-600">
                <Settings2 size={14} />
                최대 50MB
               </span>
               <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-4 py-1.5 text-sm font-bold text-slate-600">
                <FileUp size={14} />
                PDF 형식
               </span>
            </div>

            {flowError && (
              <div className="mt-4 max-w-sm w-full text-center p-3 bg-red-50 text-red-600 rounded-xl font-bold text-sm">
                {flowError}
              </div>
            )}
            
            {!isUploading && (
               <div className="text-slate-400 text-sm font-medium mt-4">
                 좌측의 정보를 모두 입력한 후 파일을 업로드해주세요.
               </div>
            )}
          </div>
        </div>

      </div>

      {/* 생활기록부 PDF 발급 안내 가이드 */}
      <div className="mt-8 rounded-3xl border border-slate-100 bg-white p-6 shadow-sm">
        <div className="mb-6">
          <h3 className="text-lg font-black text-slate-900 flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 text-xs font-black">?</span>
            학교생활기록부 PDF 발급 방법을 모르시겠나요?
          </h3>
          <p className="text-xs font-bold text-slate-400 mt-1">
            아래의 국가 공식 발급처 및 모바일 간편 전자문서 지갑을 통해 1분 만에 생활기록부를 조회하고 PDF 파일로 즉시 다운로드하실 수 있습니다.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 정부 24 카드 */}
          <div className="group relative overflow-hidden rounded-2xl border border-slate-100 bg-slate-50/50 p-5 transition-all duration-300 hover:border-blue-200 hover:bg-blue-50/10 hover:shadow-xl hover:shadow-blue-100/20">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#003580] text-white shadow-md shadow-blue-100 group-hover:scale-105 transition-transform duration-300">
                  <svg viewBox="0 0 100 100" className="h-7 w-7" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="50" cy="50" r="45" fill="#003580" />
                    <path d="M 50 18 A 32 32 0 0 1 50 82 A 16 16 0 0 1 50 50 A 16 16 0 0 0 50 18" fill="#C60C30" />
                    <path d="M 50 18 A 32 32 0 0 1 50 82 A 16 16 0 0 0 50 50 A 16 16 0 0 1 50 18" fill="#FFFFFF" />
                    <circle cx="50" cy="50" r="8" fill="#003580" />
                  </svg>
                </div>
                <div>
                  <h4 className="text-base font-black text-slate-800">정부24 웹사이트 발급</h4>
                  <p className="text-[11px] font-bold text-slate-400">PC 및 웹브라우저를 통해 고화질 다운로드</p>
                </div>
              </div>
              <a
                href="https://www.gov.kr"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-8 items-center gap-1 rounded-xl bg-blue-600 px-3.5 text-xs font-black text-white shadow-md shadow-blue-200 hover:bg-blue-700 transition-colors duration-200"
              >
                정부24 바로가기
              </a>
            </div>

            <div className="mt-5 space-y-3 border-t border-slate-100/60 pt-4">
              <div className="flex gap-2 text-xs font-bold text-slate-600">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-[10px] font-black text-blue-700">1</span>
                <span className="leading-5"><strong className="text-slate-800">정부24</strong> 공식 포털 접속 후 간편/공동인증 로그인</span>
              </div>
              <div className="flex gap-2 text-xs font-bold text-slate-600">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-[10px] font-black text-blue-700">2</span>
                <span className="leading-5">통합검색에 <strong className="text-slate-800">'학교생활기록부(초중고)'</strong> 입력 및 신청</span>
              </div>
              <div className="flex gap-2 text-xs font-bold text-slate-600">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-[10px] font-black text-blue-700">3</span>
                <span className="leading-5">수령방법을 <strong className="text-indigo-600">'온라인발급'</strong>으로 선택해 최종 문서 생성</span>
              </div>
              <div className="flex gap-2 text-xs font-bold text-slate-600">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-[10px] font-black text-blue-700">4</span>
                <span className="leading-5">출력 화면에서 인쇄 대상을 <strong className="text-indigo-600">'PDF로 저장'</strong>으로 선택해 저장</span>
              </div>
            </div>
          </div>

          {/* 카카오 지갑 카드 */}
          <div className="group relative overflow-hidden rounded-2xl border border-slate-100 bg-slate-50/50 p-5 transition-all duration-300 hover:border-amber-200 hover:bg-amber-50/10 hover:shadow-xl hover:shadow-amber-100/20">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#FEE500] shadow-md shadow-amber-100 group-hover:scale-105 transition-transform duration-300">
                  <svg viewBox="0 0 24 24" className="h-6 w-6 fill-[#3C1E1E]" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 3c-5.523 0-10 3.582-10 8 0 2.946 1.984 5.53 4.968 6.91-.32 1.155-1.156 4.172-1.325 4.814-.21.802.28.791.583.589.237-.158 3.738-2.54 5.223-3.551.183.023.368.038.551.038 5.523 0 10-3.582 10-8s-4.477-8-10-8z" />
                  </svg>
                </div>
                <div>
                  <h4 className="text-base font-black text-slate-800">카카오톡 지갑 발급</h4>
                  <p className="text-[11px] font-bold text-slate-400">모바일 앱에서 간편 발급 및 즉시 파일 전송</p>
                </div>
              </div>
              <a
                href="https://wallet.kakao.com"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-8 items-center gap-1 rounded-xl bg-[#FEE500] px-3.5 text-xs font-black text-[#191919] shadow-md shadow-amber-100 hover:bg-[#FDE200] transition-colors duration-200"
              >
                카카오 지갑 바로가기
              </a>
            </div>

            <div className="mt-5 space-y-3 border-t border-slate-100/60 pt-4">
              <div className="flex gap-2 text-xs font-bold text-slate-600">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-100 text-[10px] font-black text-amber-800">1</span>
                <span className="leading-5">카카오톡 실행 후 우측 하단 <strong className="text-slate-800">'더보기(...)'</strong> 탭 클릭</span>
              </div>
              <div className="flex gap-2 text-xs font-bold text-slate-600">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-100 text-[10px] font-black text-amber-800">2</span>
                <span className="leading-5">프로필 하단 <strong className="text-slate-800">'지갑'</strong> 혹은 <strong className="text-slate-800">'전자문서'</strong> 버튼 터치</span>
              </div>
              <div className="flex gap-2 text-xs font-bold text-slate-600">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-100 text-[10px] font-black text-amber-800">3</span>
                <span className="leading-5">신규 신청 리스트 중 <strong className="text-slate-800">'학교생활기록부'</strong> 선택 후 인증</span>
              </div>
              <div className="flex gap-2 text-xs font-bold text-slate-600">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-100 text-[10px] font-black text-amber-800">4</span>
                <span className="leading-5">생성된 전자문서를 확인하고 우측 상단 메뉴를 통해 <strong className="text-amber-800">'저장'</strong></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};
