import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { ArrowRight, Compass, Lightbulb, Link2, Sparkles, Target } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { DIAGNOSIS_STORAGE_KEY } from '../lib/diagnosis';
import { extractDiagnosisMajorDirectionCandidates } from '../lib/chatbotMode';
import {
  MAJOR_TREND_PLAYBOOK,
  buildMajorChipLabels,
  buildWorkshopPrompt,
  resolveTrendMajorKey,
  type MajorTrendTopic,
  type TrendLens,
  type TrendMajorKey,
} from '../lib/trendCopilot';
import orbitIllustration from '../assets/illustration-orbit.svg';
import depthIllustration from '../assets/illustration-depth-grid.svg';

interface TrendLocationState {
  major?: string;
  projectId?: string;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asText(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const normalized = value.trim();
  return normalized || null;
}

function readDiagnosisStorageSnapshot(): Record<string, unknown> | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(DIAGNOSIS_STORAGE_KEY);
    if (!raw) return null;
    return asRecord(JSON.parse(raw));
  } catch (error) {
    console.error('Failed to parse diagnosis storage for trend copilot:', error);
    return null;
  }
}

function resolveWorkshopPath(projectId: string | null): string {
  if (!projectId) return '/app/workshop';
  return `/app/workshop/${encodeURIComponent(projectId)}`;
}

function summaryLine(value: unknown, fallback: string): string {
  const text = asText(value);
  return text || fallback;
}

function compactLine(value: string, max = 48): string {
  if (value.length <= max) return value;
  return `${value.slice(0, max).trim()}…`;
}

const majorPalette: Record<TrendMajorKey, { chip: string; chipIdle: string; panel: string; button: string; tag: string }> = {
  건축: {
    chip: 'bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-[0_10px_20px_rgba(234,88,12,0.28)]',
    chipIdle: 'border-amber-200 text-amber-800 hover:bg-amber-50',
    panel: 'from-amber-500/90 via-orange-500/85 to-rose-500/75',
    button: 'bg-amber-600 hover:bg-amber-700',
    tag: 'text-amber-700 bg-amber-50 border-amber-200',
  },
  컴공: {
    chip: 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-[0_10px_20px_rgba(37,99,235,0.28)]',
    chipIdle: 'border-cyan-200 text-cyan-800 hover:bg-cyan-50',
    panel: 'from-cyan-500/90 via-sky-500/85 to-indigo-500/75',
    button: 'bg-sky-600 hover:bg-sky-700',
    tag: 'text-sky-700 bg-sky-50 border-sky-200',
  },
  바이오: {
    chip: 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-[0_10px_20px_rgba(5,150,105,0.28)]',
    chipIdle: 'border-emerald-200 text-emerald-800 hover:bg-emerald-50',
    panel: 'from-emerald-500/90 via-teal-500/85 to-cyan-500/75',
    button: 'bg-emerald-600 hover:bg-emerald-700',
    tag: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  },
  경영: {
    chip: 'bg-gradient-to-r from-fuchsia-500 to-rose-500 text-white shadow-[0_10px_20px_rgba(225,29,72,0.24)]',
    chipIdle: 'border-rose-200 text-rose-800 hover:bg-rose-50',
    panel: 'from-fuchsia-500/90 via-rose-500/85 to-orange-500/75',
    button: 'bg-rose-600 hover:bg-rose-700',
    tag: 'text-rose-700 bg-rose-50 border-rose-200',
  },
  사회과학: {
    chip: 'bg-gradient-to-r from-violet-500 to-purple-500 text-white shadow-[0_10px_20px_rgba(139,92,246,0.3)]',
    chipIdle: 'border-violet-200 text-violet-800 hover:bg-violet-50',
    panel: 'from-violet-500/90 via-purple-500/85 to-indigo-500/75',
    button: 'bg-violet-600 hover:bg-violet-700',
    tag: 'text-violet-700 bg-violet-50 border-violet-200',
  },
  디자인: {
    chip: 'bg-gradient-to-r from-pink-500 to-fuchsia-500 text-white shadow-[0_10px_20px_rgba(236,72,153,0.28)]',
    chipIdle: 'border-pink-200 text-pink-800 hover:bg-pink-50',
    panel: 'from-pink-500/90 via-fuchsia-500/85 to-violet-500/75',
    button: 'bg-pink-600 hover:bg-pink-700',
    tag: 'text-pink-700 bg-pink-50 border-pink-200',
  },
};

export function Trends() {
  const navigate = useNavigate();
  const location = useLocation();
  const routeState = (location.state as TrendLocationState | null) ?? null;

  const explicitMajorFromQuery = useMemo(() => {
    const major = new URLSearchParams(location.search).get('major');
    return major?.trim() || null;
  }, [location.search]);
  const explicitMajor = routeState?.major?.trim() || explicitMajorFromQuery;

  const storedDiagnosis = useMemo(readDiagnosisStorageSnapshot, []);
  const storedDiagnosisPayload = asRecord(storedDiagnosis?.diagnosis) ?? null;
  const inferredMajorTop3 = useMemo(
    () => extractDiagnosisMajorDirectionCandidates(storedDiagnosisPayload, 3),
    [storedDiagnosisPayload],
  );

  const majorChips = useMemo(
    () =>
      buildMajorChipLabels({
        explicitMajor,
        inferredMajors: inferredMajorTop3,
      }),
    [explicitMajor, inferredMajorTop3],
  );

  const [selectedMajor, setSelectedMajor] = useState<string>(majorChips[0] || '컴공');
  const [activeLens, setActiveLens] = useState<TrendLens>('flow');
  const [showRecordConnection, setShowRecordConnection] = useState(false);

  useEffect(() => {
    if (!majorChips.length) return;
    if (!majorChips.includes(selectedMajor)) {
      setSelectedMajor(majorChips[0]);
    }
  }, [majorChips, selectedMajor]);

  const majorKey = resolveTrendMajorKey(selectedMajor);
  const trendTopics = MAJOR_TREND_PLAYBOOK[majorKey];
  const palette = majorPalette[majorKey];

  const diagnosisSummary = asRecord(storedDiagnosisPayload?.diagnosis_summary_json) ?? null;
  const diagnosisContext = asRecord(storedDiagnosisPayload?.chatbot_context_json) ?? null;
  const storedProjectId = asText(storedDiagnosis?.projectId);
  const projectId = routeState?.projectId?.trim() || storedProjectId || null;
  const workshopPath = resolveWorkshopPath(projectId);

  const sourceLabel = explicitMajor
    ? '목표 전공 기준'
    : inferredMajorTop3.length > 0
      ? '진단 Top 3 기준'
      : '기본 전공 기준';

  const handleStartWorkshop = (topic?: MajorTrendTopic) => {
    const prompt = topic ? buildWorkshopPrompt(topic, selectedMajor) : undefined;
    navigate(workshopPath, {
      state: {
        major: selectedMajor,
        chatbotMode: 'trend',
        fromTrend: true,
        trendTopicId: topic?.id ?? null,
        trendPrompt: prompt ?? null,
        projectId: projectId ?? undefined,
      },
    });
    toast.success(topic ? '선택 주제로 워크숍을 열었습니다.' : '트렌드 모드로 워크숍을 열었습니다.');
  };

  const recordLinkHint = [
    summaryLine(diagnosisSummary?.headline, '진단 헤드라인 없음'),
    summaryLine(diagnosisSummary?.recommended_focus, '추천 초점 없음'),
    summaryLine(
      diagnosisContext?.major_alignment_hints && Array.isArray(diagnosisContext.major_alignment_hints)
        ? diagnosisContext.major_alignment_hints[0]
        : null,
      '전공 연계 힌트 없음',
    ),
  ];

  const lensItems: Array<{ key: TrendLens; label: string; icon: React.ComponentType<{ size?: number }> }> = [
    { key: 'flow', label: '흐름', icon: Sparkles },
    { key: 'question', label: '질문', icon: Target },
    { key: 'activity', label: '활동', icon: Lightbulb },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-3 py-4 sm:px-5 sm:py-7">
      <motion.section
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-[2rem] border border-white/70 bg-white/80 p-5 shadow-[0_26px_52px_-36px_rgba(15,23,42,0.55)] backdrop-blur-md sm:p-7"
      >
        <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-fuchsia-200/45 blur-3xl" />
        <div className="pointer-events-none absolute -left-12 bottom-2 h-44 w-44 rounded-full bg-cyan-200/45 blur-3xl" />

        <div className="grid items-center gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-black text-slate-700">
              <Compass size={14} />
              Major Trend Copilot
            </div>

            <h1 className="text-2xl font-black text-slate-900 sm:text-3xl">
              {selectedMajor} 탐구주제 모드
            </h1>

            <div className="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-extrabold text-slate-600">
              {sourceLabel}
            </div>

            <div className="flex flex-wrap gap-2">
              {majorChips.map((chip) => {
                const chipKey = resolveTrendMajorKey(chip);
                const chipPalette = majorPalette[chipKey];
                const selected = chip === selectedMajor;
                return (
                  <button
                    key={chip}
                    type="button"
                    onClick={() => {
                      setSelectedMajor(chip);
                      setShowRecordConnection(false);
                    }}
                    className={`rounded-full border px-3 py-1.5 text-sm font-extrabold transition ${
                      selected
                        ? `${chipPalette.chip} border-transparent`
                        : `bg-white ${chipPalette.chipIdle}`
                    }`}
                  >
                    {chip}
                  </button>
                );
              })}

              <button
                type="button"
                onClick={() => setShowRecordConnection((prev) => !prev)}
                className={`rounded-full border px-3 py-1.5 text-sm font-extrabold transition ${
                  showRecordConnection
                    ? 'border-emerald-500 bg-emerald-600 text-white shadow-[0_10px_20px_rgba(5,150,105,0.24)]'
                    : 'border-emerald-200 bg-white text-emerald-700 hover:bg-emerald-50'
                }`}
              >
                내 학생부와 연결하기
              </button>
            </div>

            <div className="flex flex-wrap gap-2">
              {lensItems.map((lens) => (
                <button
                  key={lens.key}
                  type="button"
                  onClick={() => setActiveLens(lens.key)}
                  className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-bold transition ${
                    activeLens === lens.key
                      ? 'bg-slate-900 text-white'
                      : 'border border-slate-200 bg-white text-slate-600 hover:border-slate-400'
                  }`}
                >
                  <lens.icon size={14} />
                  {lens.label}
                </button>
              ))}
            </div>
          </div>

          <div className="tilt-3d relative rounded-[1.8rem] border border-white/70 bg-white/84 p-3 shadow-[0_22px_40px_-28px_rgba(15,23,42,0.55)]">
            <img src={orbitIllustration} alt="전공 트렌드 일러스트" className="h-auto w-full rounded-2xl" />
            <img
              src={depthIllustration}
              alt="전공 탐색 레이어 일러스트"
              className="absolute -bottom-5 right-4 w-[48%] rounded-2xl border border-white/70 bg-white/84 shadow-[0_16px_30px_-22px_rgba(15,23,42,0.45)]"
            />
          </div>
        </div>
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="space-y-4"
      >
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => handleStartWorkshop()}
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-bold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            워크숍으로 가져가기
            <ArrowRight size={14} />
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {trendTopics.map((topic, index) => {
            const topicLine = activeLens === 'flow' ? topic.flow : activeLens === 'question' ? topic.question : topic.activity;
            return (
              <motion.article
                key={topic.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.35, delay: index * 0.05 }}
                className="tilt-3d flex h-full flex-col overflow-hidden rounded-3xl border border-white/70 bg-white/86 shadow-[0_22px_40px_-30px_rgba(15,23,42,0.55)]"
              >
                <div className={`relative h-28 bg-gradient-to-br ${palette.panel}`}>
                  <div className="absolute left-4 top-4 rounded-full bg-white/20 px-3 py-1 text-xs font-black text-white">
                    {selectedMajor}
                  </div>
                  <div className="absolute bottom-4 right-4 text-xs font-black text-white/85">0{index + 1}</div>
                </div>

                <div className="flex flex-1 flex-col p-4">
                  <h3 className="text-lg font-black text-slate-900">{topic.title}</h3>
                  <p className="mt-3 text-sm font-semibold leading-6 text-slate-600">{compactLine(topicLine, 58)}</p>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <span className={`rounded-full border px-2.5 py-1 text-[11px] font-black ${palette.tag}`}>
                      {activeLens === 'flow' ? '흐름' : activeLens === 'question' ? '질문' : '활동'}
                    </span>
                    <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-black text-slate-600">
                      실행 연결
                    </span>
                  </div>

                  <div className="mt-auto pt-4">
                    <button
                      type="button"
                      onClick={() => handleStartWorkshop(topic)}
                      className={`inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-extrabold text-white transition ${palette.button}`}
                    >
                      이 주제로 설계하기
                      <ArrowRight size={14} />
                    </button>
                  </div>
                </div>
              </motion.article>
            );
          })}
        </div>
      </motion.section>

      {showRecordConnection && (
        <motion.section
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-3xl border border-emerald-200 bg-emerald-50/70 p-4 sm:p-5"
        >
          <h2 className="mb-3 flex items-center gap-2 text-lg font-black text-emerald-900">
            <Link2 size={18} />
            학생부 연결 포인트
          </h2>

          <div className="grid gap-3 sm:grid-cols-3">
            {recordLinkHint.map((item, index) => (
              <div key={index} className="rounded-2xl border border-emerald-200 bg-white px-3 py-3 text-sm font-semibold text-emerald-900">
                {compactLine(item, 52)}
              </div>
            ))}
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => handleStartWorkshop(trendTopics[0])}
              className="rounded-full bg-emerald-600 px-3 py-1.5 text-sm font-extrabold text-white transition hover:bg-emerald-700"
            >
              주제 계획 시작
            </button>
            <button
              type="button"
              onClick={() =>
                navigate('/app/diagnosis', {
                  state: { projectId: projectId ?? undefined },
                })
              }
              className="rounded-full border border-emerald-300 bg-white px-3 py-1.5 text-sm font-extrabold text-emerald-800 transition hover:bg-emerald-100"
            >
              진단 결과 다시 보기
            </button>
          </div>
        </motion.section>
      )}
    </div>
  );
}
