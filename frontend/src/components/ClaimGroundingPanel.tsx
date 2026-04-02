import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ShieldCheck, ShieldAlert, Shield, Search, ChevronDown, ChevronUp, AlertCircle, FileSearch, Filter } from 'lucide-react';
import { type ClaimGrounding, type ClaimSupportStatus, type ClaimProvenanceType } from '@shared-contracts';

interface ClaimGroundingPanelProps {
  claims: ClaimGrounding[];
}

function StatusBadge({ status }: { status: ClaimSupportStatus }) {
  switch (status) {
    case 'supported':
      return <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-emerald-700 shadow-sm border border-emerald-200"><ShieldCheck size={12}/> Supported</span>;
    case 'weak':
      return <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-amber-700 shadow-sm border border-amber-200"><Shield size={12}/> Weakly Supported</span>;
    case 'mixed':
      return <span className="inline-flex items-center gap-1 rounded-full bg-purple-100 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-purple-700 shadow-sm border border-purple-200"><Search size={12}/> Mixed</span>;
    case 'unsupported':
      return <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-red-700 shadow-sm border border-red-200"><ShieldAlert size={12}/> Unsupported</span>;
  }
}

function ProvenanceStyle(type: ClaimProvenanceType) {
  switch (type) {
    case 'student_record':
      return 'bg-blue-50 border-blue-200 text-blue-900 border-l-4 border-l-blue-500';
    case 'external_research':
      return 'bg-amber-50 border-amber-200 text-amber-900 border-l-4 border-l-amber-500';
    case 'ai_interpretation':
      return 'bg-purple-50 border-purple-200 text-purple-900 border-l-4 border-l-purple-500';
  }
}

function ProvenanceName(type: ClaimProvenanceType) {
  switch (type) {
    case 'student_record': return 'Student Record (학생부)';
    case 'external_research': return 'External Research (외부 문헌)';
    case 'ai_interpretation': return 'AI Interpretation (AI 해석)';
  }
}

function ClaimCard({ claim }: { claim: ClaimGrounding }) {
  const [expanded, setExpanded] = useState(false);
  const provStyle = ProvenanceStyle(claim.provenance_type);
  
  return (
    <article className={`rounded-xl border shadow-sm transition-all duration-300 ${provStyle}`}>
      <div className="p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-extrabold uppercase tracking-widest text-slate-500 bg-white/50 px-2 py-0.5 rounded-md border border-slate-200/50">
              {ProvenanceName(claim.provenance_type)}
            </span>
            <span className="text-[10px] font-black text-slate-400">
               CONFIDENCE: {Math.round(claim.confidence * 100)}%
            </span>
          </div>
          <StatusBadge status={claim.support_status} />
        </div>
        
        <p className="text-base sm:text-lg font-bold text-slate-800 leading-snug break-keep">
          "{claim.claim_text}"
        </p>

        {claim.support_status === 'unsupported' && claim.unsupported_reason && (
          <div className="mt-4 rounded-lg bg-red-100/50 p-3 border border-red-200/60 flex gap-2 items-start">
             <AlertCircle size={14} className="text-red-600 mt-0.5 shrink-0" />
             <p className="text-xs font-bold text-red-800 leading-relaxed">{claim.unsupported_reason}</p>
          </div>
        )}

        {claim.source_excerpts.length > 0 && (
          <div className="mt-4">
            <button 
              onClick={() => setExpanded(!expanded)} 
              className="flex items-center gap-1.5 text-xs font-black text-slate-500 hover:text-slate-800 transition-colors"
            >
              {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              {expanded ? 'Hide Source Evidence' : `View ${claim.source_excerpts.length} Source Excerpt(s)`}
            </button>
            <AnimatePresence>
              {expanded && (
                <motion.div 
                  initial={{ height: 0, opacity: 0 }} 
                  animate={{ height: 'auto', opacity: 1 }} 
                  exit={{ height: 0, opacity: 0 }}
                  className="mt-3 space-y-2 overflow-hidden"
                >
                  {claim.source_excerpts.map((excerpt, i) => (
                    <div key={i} className="rounded-lg bg-white p-3 border border-slate-200 shadow-sm">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[9px] font-black bg-slate-100 text-slate-500 px-2 py-0.5 rounded uppercase tracking-wider border border-slate-200">{excerpt.source_label}</span>
                        {excerpt.page_number && <span className="text-[9px] font-black text-slate-400">Page {excerpt.page_number}</span>}
                        {excerpt.chunk_id && <span className="text-[9px] font-bold text-slate-300">ID: {excerpt.chunk_id}</span>}
                      </div>
                      <p className="text-xs font-medium text-slate-600 italic leading-relaxed border-l-2 border-slate-200 pl-3">
                        {excerpt.text}
                      </p>
                    </div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>
    </article>
  );
}

export function ClaimGroundingPanel({ claims }: ClaimGroundingPanelProps) {
  const [filterUnsupported, setFilterUnsupported] = useState(false);
  
  if (!claims || claims.length === 0) return null;

  const unsupportedCount = claims.filter(c => c.support_status === 'unsupported' || c.support_status === 'weak').length;
  const displayClaims = filterUnsupported 
    ? claims.filter(c => c.support_status === 'unsupported' || c.support_status === 'weak' || c.support_status === 'mixed')
    : claims;

  return (
    <div data-testid="claim-grounding-panel" className="rounded-[32px] border border-slate-200 bg-white p-6 sm:p-8 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
            <FileSearch size={22} />
          </div>
          <div>
            <h3 className="text-xl font-black text-slate-800 tracking-tight">Claim Audit & Provenance</h3>
            <p className="text-xs font-bold text-slate-400">AI-extracted claims and their evidence verification status.</p>
          </div>
        </div>
        
        <button 
          onClick={() => setFilterUnsupported(!filterUnsupported)}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-black transition-colors border ${
            filterUnsupported 
            ? 'bg-amber-100 border-amber-200 text-amber-800 shadow-sm' 
            : 'bg-slate-50 border-slate-200 text-slate-500 hover:bg-slate-100'
          }`}
        >
          <Filter size={14} />
          검증 필요 주장만 보기 {filterUnsupported ? '(Active)' : ''}
        </button>
      </div>

      <AnimatePresence>
        {unsupportedCount > 0 && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }} 
            animate={{ opacity: 1, y: 0 }} 
            className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 flex gap-3 items-start shadow-sm"
          >
            <AlertCircle className="text-red-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-black text-red-900 mb-1">주의: 증명되지 않은 주장이 포함되어 있습니다.</p>
              <p className="text-xs font-medium text-red-700 leading-relaxed">
                현재 분석에서 {unsupportedCount}개의 주장이 원본 생기부나 외부 자료로 직접 증명되지 않았습니다. '검증 필요 주장만 보기'를 눌러 항목을 수동 검토해주세요.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="space-y-4">
        <AnimatePresence mode="popLayout">
          {displayClaims.map(claim => (
            <motion.div 
              key={claim.id} 
              layout 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
            >
              <ClaimCard claim={claim} />
            </motion.div>
          ))}
          {displayClaims.length === 0 && (
            <motion.div className="py-12 text-center rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50">
               <p className="text-sm font-bold text-slate-400">조건에 맞는 주장이 없습니다.</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
