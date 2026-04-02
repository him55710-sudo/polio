import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { ArrowRight, School, Sparkles, X, Trash2, ChevronUp, ChevronDown, GripVertical } from 'lucide-react';
import { CatalogAutocompleteInput } from './CatalogAutocompleteInput';
import { CatalogMultiSelectInput } from './CatalogMultiSelectInput';
import { UniversityLogo } from './UniversityLogo';
import {
  isEducationCatalogLoaded,
  searchMajors,
  searchUniversities,
} from '../lib/educationCatalog';

interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialUniversity?: string | null;
  initialMajor?: string | null;
  initialInterests?: string[];
  isSubmitting: boolean;
  onSubmit: (payload: {
    targetUniversity: string;
    targetMajor: string;
    interestUniversities: string[];
  }) => Promise<void>;
}

const TEXT = {
  chip: '목표 대학 설정',
  title: '가고 싶은 대학을 최대 6개까지 담아보세요',
  description: '순서대로 배치하면 가장 가고 싶은 대학을 중심으로 탐구 플랜이 맞춰집니다.',
  step1: '대학 선택',
  step2: '학과 선택',
  universityLabel: '어느 대학인가요?',
  majorLabel: '희망하는 학과는요?',
  addGoal: '이 목표 추가',
  saving: '저장 중...',
  submit: '모든 정보 저장하기',
  goalListTitle: '나의 목표 대학 (최대 6개)',
  emptyGoals: '아직 추가된 대학이 없습니다.',
};

interface GoalItem {
  id: string;
  university: string;
  major: string;
}

export function OnboardingModal({
  isOpen,
  onClose,
  initialUniversity,
  initialMajor,
  initialInterests,
  isSubmitting,
  onSubmit,
}: OnboardingModalProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [currentUniv, setCurrentUniv] = useState('');
  const [currentMajor, setCurrentMajor] = useState('');
  const [goals, setGoals] = useState<GoalItem[]>([]);
  const [univInput, setUnivInput] = useState('');
  const [draggingGoalId, setDraggingGoalId] = useState<string | null>(null);
  const [dragOverGoalId, setDragOverGoalId] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setStep(1);
    setCurrentUniv('');
    setCurrentMajor('');
    setUnivInput('');
    
    const generateId = () => {
      try {
        return crypto.randomUUID();
      } catch {
        return Math.random().toString(36).substring(2) + Date.now().toString(36);
      }
    };

    const initialList: GoalItem[] = [];
    if (initialUniversity && initialMajor) {
      initialList.push({ id: generateId(), university: initialUniversity, major: initialMajor });
    }
    
    if (initialInterests && initialInterests.length > 0) {
      initialInterests.forEach(interest => {
        const match = interest.match(/^(.+)\s\((.+)\)$/);
        if (match) {
          initialList.push({ id: generateId(), university: match[1], major: match[2] });
        } else {
          initialList.push({ id: generateId(), university: interest, major: '전공 미지정' });
        }
      });
    }
    
    // Limit to 6
    setGoals(initialList.slice(0, 6));
  }, [initialInterests, initialMajor, initialUniversity, isOpen]);

  if (!isOpen) return null;

  const universitySuggestions = searchUniversities(univInput, {
    excludeNames: [currentUniv, ...goals.map(g => g.university)],
    limit: 100
  });

  const majorSuggestions = searchMajors(currentMajor, currentUniv, 20);
  
  const canAddMore = goals.length < 6;
  const canAddThis = (currentUniv.trim().length >= 2 || univInput.trim().length >= 2) && currentMajor.trim().length >= 2;
  const logoPreviewName = (currentUniv || univInput).trim();

  const handleAddGoal = () => {
    const univ = currentUniv || univInput.trim();
    if (!univ || currentMajor.trim().length < 2 || !canAddMore) return;
    
    const generateId = () => {
      try {
        return crypto.randomUUID();
      } catch {
        return Math.random().toString(36).substring(2) + Date.now().toString(36);
      }
    };
    
    setGoals(prev => [...prev, { id: generateId(), university: univ, major: currentMajor.trim() }]);
    setCurrentUniv('');
    setCurrentMajor('');
    setUnivInput('');
    setStep(1);
  };

  const removeGoal = (id: string) => setGoals(prev => prev.filter(g => g.id !== id));
  
  const moveGoal = (index: number, direction: 'up' | 'down') => {
    const newGoals = [...goals];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= goals.length) return;
    [newGoals[index], newGoals[targetIndex]] = [newGoals[targetIndex], newGoals[index]];
    setGoals(newGoals);
  };

  const moveGoalByDrag = (sourceId: string, targetId: string) => {
    if (!sourceId || !targetId || sourceId === targetId) return;
    setGoals(previous => {
      const sourceIndex = previous.findIndex(item => item.id === sourceId);
      const targetIndex = previous.findIndex(item => item.id === targetId);
      if (sourceIndex < 0 || targetIndex < 0) return previous;

      const next = [...previous];
      const [moved] = next.splice(sourceIndex, 1);
      next.splice(targetIndex, 0, moved);
      return next;
    });
  };

  const onGoalDragEnd = () => {
    setDraggingGoalId(null);
    setDragOverGoalId(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="relative w-full max-w-2xl rounded-[32px] bg-white p-8 shadow-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <button
          type="button"
          aria-label="온보딩 모달 닫기"
          onClick={onClose}
          className="absolute right-6 top-6 text-slate-400 hover:text-slate-600"
        >
          <X size={24}/>
        </button>

        <div className="mb-6">
          <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-[11px] font-black text-blue-600">
            <Sparkles size={12}/> {TEXT.chip}
          </div>
          <h2 className="text-3xl font-black text-slate-900">{TEXT.title}</h2>
          <p className="mt-2 text-sm text-slate-500">{TEXT.description}</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Current Selection */}
          <div className="space-y-6">
            <div className="p-5 border-2 border-slate-100 rounded-3xl space-y-4">
              <div className="flex items-center gap-2 text-xs font-black text-blue-600">
                <div className="w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center">{step}</div>
                {step === 1 ? TEXT.step1 : TEXT.step2}
              </div>
              
              {step === 1 ? (
                <div className="space-y-3">
                  <CatalogMultiSelectInput
                    label={TEXT.universityLabel}
                    selectedUniversities={currentUniv ? [currentUniv] : []}
                    representativeUniversity={currentUniv}
                    suggestions={universitySuggestions}
                    inputValue={univInput}
                    onInputChange={setUnivInput}
                    onAdd={name => { setCurrentUniv(name); setUnivInput(''); setStep(2); }}
                    onRemove={() => setCurrentUniv('')}
                    placeholder="예: 서울대학교"
                    onSetRepresentative={()=>{}}
                    emptyText="목록에 없어도 직접 입력 가능합니다."
                  />
                  {logoPreviewName.length >= 2 ? (
                    <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2">
                      <UniversityLogo
                        universityName={logoPreviewName}
                        className="h-7 w-7 rounded-md bg-slate-50 object-contain p-0.5"
                        fallbackClassName="border border-slate-200"
                      />
                      <span className="text-xs font-semibold text-slate-500">{logoPreviewName}</span>
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="p-3 bg-slate-50 rounded-2xl flex items-center justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-2">
                      <UniversityLogo
                        universityName={currentUniv || univInput}
                        className="h-7 w-7 rounded-md bg-white object-contain p-0.5 shadow-sm"
                        fallbackClassName="border border-blue-100"
                      />
                      <span className="truncate text-sm font-bold text-slate-700">{currentUniv || univInput}</span>
                    </div>
                    <button onClick={()=>setStep(1)} className="text-[10px] font-black text-blue-600 underline">변경</button>
                  </div>
                  <CatalogAutocompleteInput
                    label={TEXT.majorLabel}
                    value={currentMajor}
                    onChange={setCurrentMajor}
                    placeholder="예: 경영학과"
                    suggestions={majorSuggestions}
                    onSelect={s => setCurrentMajor(s.label)}
                    autoFocus
                  />
                  <button onClick={handleAddGoal} disabled={!canAddThis || !canAddMore} className="w-full py-3 bg-blue-600 text-white rounded-2xl font-black text-sm disabled:opacity-30">
                    {TEXT.addGoal} (+{goals.length}/6)
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Right: Goals List & Reorder */}
          <div className="space-y-4">
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest">{TEXT.goalListTitle}</h3>
            {goals.length > 1 ? <p className="text-xs font-semibold text-slate-500">카드를 드래그해서 순서를 자유롭게 조정할 수 있습니다.</p> : null}
            {goals.length === 0 ? (
              <div className="h-40 flex flex-col items-center justify-center border-2 border-dashed border-slate-100 rounded-3xl text-slate-300 text-sm font-medium">
                <School size={32} className="mb-2 opacity-20"/> {TEXT.emptyGoals}
              </div>
            ) : (
              <div className="space-y-2">
                {goals.map((g, idx) => (
                  <motion.div
                    key={g.id}
                    layout
                    draggable
                    onDragStart={() => setDraggingGoalId(g.id)}
                    onDragOver={event => {
                      event.preventDefault();
                      setDragOverGoalId(g.id);
                    }}
                    onDrop={() => {
                      if (draggingGoalId) moveGoalByDrag(draggingGoalId, g.id);
                      onGoalDragEnd();
                    }}
                    onDragEnd={onGoalDragEnd}
                    className={`flex items-center gap-3 rounded-2xl border p-3 transition-all ${
                      dragOverGoalId === g.id ? 'border-blue-300 bg-blue-50' : 'border-slate-100 bg-slate-50'
                    } ${draggingGoalId === g.id ? 'opacity-60' : ''}`}
                  >
                    <div className="flex items-center gap-1 text-slate-400">
                      <GripVertical size={16} />
                      <div className="flex flex-col gap-1">
                        <button onClick={()=>moveGoal(idx, 'up')} disabled={idx===0} className="text-slate-300 hover:text-blue-500 disabled:opacity-30"><ChevronUp size={16}/></button>
                        <button onClick={()=>moveGoal(idx, 'down')} disabled={idx===goals.length-1} className="text-slate-300 hover:text-blue-500 disabled:opacity-30"><ChevronDown size={16}/></button>
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-black text-slate-400">Target {idx+1}</p>
                      <p className="text-sm font-black text-slate-800 truncate">{g.university}</p>
                      <p className="text-[11px] font-medium text-slate-500 truncate">{g.major}</p>
                    </div>
                    <UniversityLogo
                      universityName={g.university}
                      className="h-10 w-10 rounded-lg bg-white object-contain p-1 shadow-sm"
                      fallbackClassName="border border-slate-200"
                    />
                    <button onClick={()=>removeGoal(g.id)} className="p-2 text-slate-300 hover:text-red-500 transition-colors"><Trash2 size={16}/></button>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="mt-10 pt-6 border-t">
          <button 
            disabled={goals.length === 0 || isSubmitting}
            onClick={() => {
              const main = goals[0];
              const others = goals.slice(1).map(g => `${g.university} (${g.major})`);
              void onSubmit({ targetUniversity: main.university, targetMajor: main.major, interestUniversities: others });
            }}
            className="w-full py-4 bg-slate-900 text-white rounded-2xl font-black text-lg flex items-center justify-center gap-2 hover:bg-black transition-all disabled:opacity-40"
          >
            {isSubmitting ? TEXT.saving : TEXT.submit} <ArrowRight size={20}/>
          </button>
        </div>
      </motion.div>
    </div>
  );
}
