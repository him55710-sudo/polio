const fs = require('fs');
const path = 'c:\\Users\\임현수\\Downloads\\polio for real\\polio for real\\frontend\\src\\pages\\Workshop.tsx';
const originalContent = fs.readFileSync(path, 'utf8');

const returnStatement = `  return (
    <div className={cn("mx-auto max-w-[1800px] space-y-4 px-2.5 py-3 transition-all duration-700 sm:space-y-6 sm:px-4 sm:py-6", advancedMode && "rounded-[32px] bg-[#004aad]/5 shadow-[inset_0_0_100px_rgba(0,74,173,0.02)] sm:rounded-[48px]")}>
      <motion.div
        animate={advancedMode ? { y: [0, -2, 0] } : {}}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      >
        <PageHeader
          eyebrow="워크숍"
          title="유니폴리 초안 작업"
          description="업로드된 기록 근거를 바탕으로 초안을 안정적으로 이어서 작성해보세요."
          actions={
            <div className="flex items-center gap-2">
              <SecondaryButton
                data-testid="workshop-advanced-toggle"
                onClick={() => setAdvancedMode(prev => !prev)}
                aria-label={advancedMode ? '고급 모드 끄기' : '고급 모드 켜기'}
              >
                {advancedMode ? <ToggleRight size={16} /> : <ToggleLeft size={16} />}
                {advancedMode ? '고급 모드' : '기본 모드'}
              </SecondaryButton>
              <SecondaryButton
                onClick={handleGenerateDraft}
                disabled={!workshopState || isRendering || !workshopState.render_requirements?.can_render}
              >
                {isRendering ? <Loader2 size={16} className="animate-spin" /> : <Presentation size={14} />}
                미리보기 생성
              </SecondaryButton>
            </div>
          }
          evidence={
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={isProjectBacked ? 'success' : 'warning'}>
                {isProjectBacked ? '프로젝트 연결' : '데모 모드'}
              </StatusBadge>
              {isProjectBacked && (
                <StatusBadge status={guidedSetupComplete ? 'success' : 'warning'}>
                  {guidedSetupComplete ? '가이드 설정 완료' : \`가이드 진행: \${guidedPhaseLabel}\`}
                </StatusBadge>
              )}
              <StatusBadge status={qualityMeta.status}>{qualityMeta.label}</StatusBadge>
            </div>
          }
        />

        <div className="mt-6 lg:hidden">
          <div className="inline-flex w-full items-center gap-1 rounded-2xl border border-slate-200 bg-white p-1 shadow-sm">
            <button
              type="button"
              onClick={() => setMobileView('chat')}
              className={cn(
                'h-10 flex-1 rounded-xl px-3 text-sm font-bold transition-all',
                mobileView === 'chat' ? 'bg-[#004aad] text-white shadow-md' : 'text-slate-600 hover:bg-slate-50',
              )}
            >
              채팅
            </button>
            <button
              type="button"
              onClick={() => setMobileView('draft')}
              className={cn(
                'h-10 flex-1 rounded-xl px-3 text-sm font-bold transition-all',
                mobileView === 'draft' ? 'bg-[#004aad] text-white shadow-md' : 'text-slate-600 hover:bg-slate-50',
              )}
            >
              문서
            </button>
          </div>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[400px_minmax(0,1fr)] xl:grid-cols-[460px_minmax(0,1fr)]">
          <SectionCard
            title="유니폴리 채팅"
            eyebrow="대화"
            className={cn(
              'flex min-h-0 flex-col h-[calc(100dvh-15rem)] min-h-[520px] max-h-[800px]',
              mobileView !== 'chat' && 'hidden lg:flex'
            )}
            bodyClassName="relative flex min-h-0 flex-1 flex-col overflow-hidden p-0"
          >
            <div className="flex h-full flex-col">
              <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6 scroll-smooth">
                {limitedModeNotice && (
                  <WorkflowNotice
                    tone="warning"
                    title={limitedModeNotice.title}
                    description={limitedModeNotice.description}
                    className="mb-4"
                  />
                )}

                {workshopState?.render_requirements && (
                  <div className="mb-2 border-b border-slate-100 bg-slate-50/30 px-4 py-4">
                    <WorkshopProgress 
                      requirements={workshopState.render_requirements} 
                      qualityInfo={workshopState.quality_level_info}
                    />
                  </div>
                )}

                {diagnosisReport && (
                  <SurfaceCard tone="muted" padding="none" className="mb-4 overflow-hidden border-[#004aad]/10 bg-[#004aad]/5">
                    <button
                      type="button"
                      onClick={() => setShowDiagnosis(prev => !prev)}
                      className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-bold text-slate-700 hover:bg-[#004aad]/10"
                    >
                      <span className="inline-flex items-center gap-2">
                        <div className="h-1.5 w-1.5 rounded-full bg-[#004aad] shadow-sm shadow-[#004aad]/50" />
                        최근 생기부 진단 정보
                      </span>
                      {showDiagnosis ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                    <AnimatePresence>
                      {showDiagnosis && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden border-t border-[#004aad]/10 px-4 pb-4"
                        >
                          <SurfaceCard padding="sm" className="mt-3 space-y-2 border-none bg-white/60">
                            <p className="text-sm font-bold text-slate-900">{diagnosisHeadline}</p>
                            <div className="flex flex-wrap items-center gap-2">
                              <StatusBadge status={diagnosisRiskStatus}>{diagnosisRiskLabel}</StatusBadge>
                              {diagnosisGapCount > 0 && (
                                <span className="text-xs font-medium text-slate-500">발견된 보완점: {diagnosisGapCount}개</span>
                              )}
                            </div>
                          </SurfaceCard>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </SurfaceCard>
                )}

                {messages.map((message) => (
                  <MessageItem
                    key={message.id}
                    message={message}
                    onApplyPatch={handleApplyPatchFromMessage}
                    onGuidedChoiceSelect={(groupId, option) => handleGuidedChoiceSelect(groupId, option, message)}
                    isLastInPhase={false}
                  />
                ))}
                {isTyping && <FoliTypingIndicator />}
                <div ref={messagesEndRef} />
              </div>

              <div className="border-t border-slate-100 p-4">
                <div className="flex gap-2">
                  <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        void handleSend();
                      }
                    }}
                    placeholder={inputPlaceholder}
                    disabled={isTyping || !!isSelectingGuidedTopicId || isGuidedActionLoading}
                    className="flex-1 h-12 rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 text-[15px] font-medium text-slate-900 outline-none transition-all placeholder:text-slate-400 focus:border-[#004aad] disabled:opacity-50"
                  />
                  <button
                    type="button"
                    onClick={() => void handleSend()}
                    disabled={!input.trim() || isTyping || !!isSelectingGuidedTopicId || isGuidedActionLoading}
                    className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#004aad] text-white shadow-lg shadow-[#004aad]/20 transition-all hover:bg-[#003a8a] disabled:bg-slate-200"
                  >
                    {isTyping ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
                  </button>
                </div>
              </div>
            </div>
          </SectionCard>

          <SectionCard
            title="초안 문서"
            description="유니폴리가 제안한 내용을 바탕으로 구성한 문서입니다. 자유롭게 수정하고 보강해 주세요."
            eyebrow="초안 작성"
            className={cn(
              'flex min-h-0 flex-col h-[calc(100dvh-15rem)] min-h-[520px] max-h-[800px]',
              mobileView !== 'draft' && 'hidden lg:flex'
            )}
            bodyClassName="flex min-h-0 flex-1 flex-col overflow-hidden p-0"
            actions={
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowDraftControls(prev => !prev)}
                  className="inline-flex h-9 items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-600 transition-colors hover:bg-slate-50"
                >
                  {showDraftControls ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  초안 옵션
                </button>
                <SecondaryButton size="sm" onClick={handleOpenProfessionalEditor}>
                  <PenSquare size={14} className="mr-1.5" />
                  전문 편집기
                </SecondaryButton>
                <PrimaryButton size="sm" onClick={handleSaveDraft}>
                  <Save size={14} className="mr-1.5" />
                  저장
                </PrimaryButton>
                <SecondaryButton size="sm" onClick={() => {
                  const blob = new Blob([documentContent], { type: 'text/markdown' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = fileName.replace('.hwpx', '.md');
                  a.click();
                  URL.revokeObjectURL(url);
                }}>
                  <Download size={14} className="mr-1.5" />
                  마크다운
                </SecondaryButton>
              </div>
            }
          >
            <div className={cn("flex flex-1 flex-col overflow-hidden p-3 sm:p-4", advancedMode && "lg:flex-row gap-4")}>
              <div className={cn("flex flex-1 flex-col overflow-y-auto pr-1 custom-scrollbar space-y-4", advancedMode && "lg:w-1/2")}>
                {isDraftOutOfSync ? (
                  <WorkflowNotice
                    tone="warning"
                    title="초안 동기화 충돌이 감지되었습니다"
                    description="서버 최신본과 자동 병합 후 다시 저장되었습니다. 병합된 내용을 빠르게 확인해 주세요."
                    className="mb-3"
                  />
                ) : null}

                {pendingDraftPatch ? (
                  <SurfaceCard tone="muted" className="mb-3 border-[#004aad]/10 bg-[#004aad]/5 p-3">
                    <p className="text-xs font-black uppercase tracking-wide text-[#004aad]">섹션 제안 대기</p>
                    <p className="mt-1 text-sm font-bold text-slate-900">
                      {pendingDraftPatch.heading || pendingDraftPatch.block_id}
                    </p>
                    {pendingDraftPatch.rationale ? (
                      <p className="mt-1 text-xs font-medium text-slate-600">{pendingDraftPatch.rationale}</p>
                    ) : null}
                    {pendingDraftPatch.evidence_boundary_note ? (
                      <p className="mt-1 text-xs font-semibold text-amber-700">
                        근거 경계: {pendingDraftPatch.evidence_boundary_note}
                      </p>
                    ) : null}
                    <div className="mt-2 flex items-center gap-2">
                      <PrimaryButton size="sm" onClick={() => applyPatchToDraft(pendingDraftPatch, true, false)}>
                        초안에 반영
                      </PrimaryButton>
                      <SecondaryButton size="sm" onClick={() => setPendingDraftPatch(null)}>
                        제안으로 유지
                      </SecondaryButton>
                    </div>
                  </SurfaceCard>
                ) : null}

                {showDraftControls ? (
                  <div className="space-y-3">
                    <div className="grid gap-2 sm:grid-cols-4">
                      {WORKSHOP_MODE_OPTIONS.map((option) => (
                        <button
                          key={option.id}
                          type="button"
                          onClick={() => {
                            setWorkshopMode(option.id);
                            setStructuredDraft((prev) => ({ ...prev, mode: option.id }));
                          }}
                          className={cn(
                            'p-2.5 rounded-xl border transition-all text-xs font-semibold text-left',
                            workshopMode === option.id
                              ? 'border-[#004aad]/20 bg-[#004aad]/5 shadow-sm'
                              : 'border-slate-200 bg-white hover:border-slate-300',
                          )}
                        >
                          <p className="text-xs font-black text-slate-800">{option.label}</p>
                          <p className="mt-0.5 text-[11px] font-medium leading-4 text-slate-500">{option.description}</p>
                        </button>
                      ))}
                    </div>

                    <WorkflowNotice
                      tone={coauthoringTier === 'pro' ? 'success' : coauthoringTier === 'plus' ? 'info' : 'warning'}
                      title={
                        coauthoringTier === 'pro'
                          ? '고급 공동작성'
                          : coauthoringTier === 'plus'
                            ? '확장 공동작성'
                            : '기본 공동작성'
                      }
                      description={
                        coauthoringTier === 'basic'
                          ? 'AI 제안은 승인 후 반영됩니다. 학생 작성 내용은 자동 덮어쓰기되지 않습니다.'
                          : '채팅 중 섹션 제안이 실시간으로 연결됩니다. 승인 전에는 학생 작성 문단을 보호합니다.'
                      }
                    />
                  </div>
                ) : null}

                {DRAFT_DEFINITION.map((definition) => {
                  const block = structuredDraft.blocks[definition.id];
                  if (!block) return null;
                  const attributionStatus = block.attribution === 'ai' ? 'success' : block.attribution === 'hybrid' ? 'info' : 'warning';
                  
                  return (
                    <SurfaceCard key={definition.id} className="border-slate-200 bg-white p-3 shadow-sm">
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <input
                          value={block.heading}
                          onChange={(event) => updateDraftHeading(definition.id, event.target.value)}
                          className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5 text-xs font-bold text-slate-800 outline-none focus:border-[#004aad] focus:bg-white"
                        />
                        <StatusBadge status={attributionStatus}>
                          {formatDraftAttributionLabel(block.attribution)}
                        </StatusBadge>
                      </div>
                      {definition.id === 'title' ? (
                        <input
                          value={block.content_markdown}
                          onChange={(event) => updateDraftBlock(definition.id, event.target.value)}
                          placeholder="제목"
                          className="h-10 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-semibold text-slate-800 outline-none focus:border-[#004aad] focus:bg-white"
                        />
                      ) : (
                        <textarea
                          value={block.content_markdown}
                          onChange={(event) => updateDraftBlock(definition.id, event.target.value)}
                          placeholder={\`\${block.heading} 내용을 작성해 주세요.\`}
                          className="min-h-[110px] w-full resize-y rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm font-medium leading-6 text-slate-800 outline-none focus:border-[#004aad] focus:bg-white"
                        />
                      )}
                    </SurfaceCard>
                  );
                })}
              </div>
              
              {advancedMode ? (
                <div className="mt-4 space-y-3 lg:mt-0 lg:w-1/2">
                  <button
                    type="button"
                    onClick={() => setShowAdvancedTools(prev => !prev)}
                    className="inline-flex h-9 items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-600 transition-colors hover:bg-slate-50"
                  >
                    {showAdvancedTools ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    고급 도구
                  </button>

                  {showAdvancedTools ? (
                    <div className="flex flex-col gap-4 overflow-y-auto pr-1 custom-scrollbar">
                      <EvidenceDrawer evidenceMap={renderArtifact?.evidence_map ?? null} />
                      <SurfaceCard className="border-[#004aad]/5 bg-[#004aad]/5 p-4 shadow-sm">
                        <AdvancedPreview
                          workshopId={workshopState?.session.id || ''}
                          artifactId={workshopState?.latest_artifact?.id || ''}
                          isAdvancedMode={advancedMode}
                          visualSpecs={renderArtifact?.visual_specs ?? []}
                          mathExpressions={renderArtifact?.math_expressions ?? []}
                          onUpdateVisualStatus={handleUpdateVisualStatus}
                          onReplaceVisual={handleReplaceVisual}
                        />
                      </SurfaceCard>
                    </div>
                  ) : (
                    <p className="text-sm font-bold text-slate-400">
                      세부 시각화 요소가 선택되었으나, 현재 환경에서는 미리보기를 제공할 수 없습니다.
                    </p>
                  )}
                </div>
              ) : null}
            </div>
          </SectionCard>
        </div>
      </motion.div>
    </div>
  );`;

// Find the return statement start
const startIndex = originalContent.indexOf('return (');
const endIndex = originalContent.lastIndexOf(');') + 2;

if (startIndex === -1 || endIndex === -1) {
  console.error('Could not find return statement.');
  process.exit(1);
}

const finalContent = originalContent.substring(0, startIndex) + returnStatement + originalContent.substring(endIndex);
fs.writeFileSync(path, finalContent, 'utf8');

// Also fix the limitedModeNotice logic above the return statement which has mojibake
const updatedFile = fs.readFileSync(path, 'utf8');
const fixedLimitedModeNotice = updatedFile.replace(/if \(limitedReason === 'evidence_gap'\) \{[^}]*title: '[^']*'[^}]*\}/g, m => {
    return \`if (limitedReason === 'evidence_gap') {
      return {
        title: '근거 보완 모드가 활성화되었습니다',
        description: '현재 확인 가능한 학생 기록이 제한되어 보수적인 제안만 제공합니다.',
      };\`;
});

// To be absolutely sure, I'll use a series of simpler replaces for the specific mojibake noticed earlier.
let contentToFix = fs.readFileSync(path, 'utf8');

const replacements = [
    { from: /title: '洹쇨굅 蹂댁셿 紐⑤뱶媛€ \?쒖꽦\?붾릺\?덉뒿\?덈떎'/g, to: "title: '근거 보완 모드가 활성화되었습니다'" },
    { from: /description: '\?꾩옱 \?뺤씤 媛€\?ν븳 \?숈깮 湲곕줉\?\?\?쒗븳\?섏뼱 蹂댁닔\?곸씤 \?쒖븞留\?\?\?쒓났\?⑸땲\?\?'/g, to: "description: '현재 확인 가능한 학생 기록이 제한되어 보수적인 제안만 제공합니다.'" },
    { from: /title: '\?쒗븳 紐⑤뱶媛€ \?쒖꽦\?붾릺\?덉뒿\?덈떎'/g, to: "title: '제한 모드가 활성화되었습니다'" },
    { from: /description: '紐⑤뜽 \?곌껐\?\?\?쇱떆\?곸쑝濡\?遺덉븞\?뺥븯\?\?\?대쾲 \?묐떟\?€ \?덉쟾\?\?湲곕낯 \?덈궡濡\?\?\?꾪솚\?섏뿀\?듬땲\?\?'/g, to: "description: '모델 연결이 일시적으로 불안정하여 이번 응답은 안전한 기본 안내로 전환되었습니다.'" },
    { from: /toast\.success\('\?뚰겕\?\?珥덉븞\?\?\?€\?ν뻽\?듬땲\?\?'\)/g, to: "toast.success('워크숍 초안이 저장되었습니다.')" }
];

replacements.forEach(r => {
    contentToFix = contentToFix.replace(r.from, r.to);
});

fs.writeFileSync(path, contentToFix, 'utf8');
console.log('Fixed Workshop.tsx structure and mojibake.');
