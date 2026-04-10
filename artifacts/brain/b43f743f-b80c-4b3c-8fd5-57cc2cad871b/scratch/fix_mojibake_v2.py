import sys

file_path = r'c:\Users\임현수\Downloads\polio for real\polio for real\frontend\src\pages\Diagnosis.tsx'

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Line numbers are 1-indexed, so we use n-1
replacements = {
    296: "      admission_type: goals.admission_type || '학생부종합',\n",
    304: "      toast.success('목표가 저장되었습니다.');\n",
    628: "        const failureMessage = getApiErrorMessage(error, '저장된 업로드 기록으로 진단을 시작하지 못했어요.');\n",
    662: "      const loadingId = toast.loading('PDF 업로드와 진단 준비를 진행 중입니다...');\n",
    704: "          const emptyContentError = 'PDF에서 진단 가능한 텍스트를 찾지 못했습니다. OCR 품질이 더 좋은 파일로 다시 시도해 주세요.';\n",
    714: "        const parseNote = parsedDocument.page_count ? `파싱 완료 (${parsedDocument.page_count}페이지)` : '파싱 완료';\n",
    792: "      label: '목표 설정',\n",
    793: "      description: '지원 목표 확정',\n",
    799: "      description: '학생부 PDF 제출',\n",
    824: "    step === 'GOALS' ? '목표가 분명할수록 진단 결과와 워크숍 추천의 정확도가 높아집니다.' :\n",
    825: "    step === 'UPLOAD' ? 'PDF 1개를 업로드하면 파싱, 마스킹, 진단이 순차적으로 진행됩니다.' :\n",
    826: "    step === 'ANALYSING' ? '근거 매핑과 위험 신호 분석을 진행 중입니다.' :\n",
    827: "    step === 'RESULT' ? '강점, 보완점, 액션 플랜을 확인한 후 워크숍으로 이동하세요.' :\n",
    828: "    '실패 원인과 작업 상태를 확인하고 안전하게 다시 시도해 주세요.';\n",
    844: "          title=\"진단 진행 타임라인\"\n",
    845: "          description=\"예상 소요 시간 대비 현재 진단 진행률을 보여드려요\"\n",
    853: "              title=\"지원 목표 목록\"\n",
    854: "              description=\"첫 번째 목표가 진단 기준점으로 사용됩니다\"\n",
    1000: "                <EmptyState title=\"설정한 목표가 없습니다\" description=\"진단을 시작하려면 최소 1개의 목표를 설정해 주세요\" />\n",
    1008: "                  목표 저장\n",
    1045: "                <p className=\"text-xl font-black tracking-tight text-slate-900\">학생부 PDF를 드래그하거나 클릭하여 업로드하세요</p>\n",
    1046: "                <p className=\"mt-2 text-base font-medium text-slate-600\">업로드 이후에 페이지를 유지하면 자동으로 상태가 갱신됩니다</p>\n",
    1072: "              title=\"문서 분석과 진단 생성을 진행 중입니다\"\n",
    1073: "              description=\"파싱이 끝나면 자동으로 진단 생성 단계로 넘어가며, 페이지를 유지하면 상태가 자동 갱신됩니다\"\n",
    1099: "                업로드로 돌아가기\n",
    1165: "                  <p className=\"mb-2 text-xs font-bold uppercase tracking-[0.14em] text-slate-400\">다음 액션</p>\n",
    1169: "                        • {action}\n",
    1181: "                title=\"추가 인사이트\"\n",
    1182: "                description=\"보조 분석 항목은 기본 화면에서 분리되어 필요할 때만 펼쳐볼 수 있어요.\"\n",
    1215: "                    <p className=\"text-xs font-bold uppercase tracking-[0.14em] text-slate-400\">권장 액션 플랜</p>\n",
    1256: "                    ? '전문 진단서가 준비되었습니다'\n",
    1259: "                        ? '진단 단계에서 문제가 발생했습니다'\n",
    1260: "                        : '진단서 생성 단계에서 문제가 발생했습니다'\n",
    1262: "                        ? '전문 진단서를 생성하고 있습니다'\n",
    1267: "                    ? '아래에서 미리보기와 PDF 다운로드를 바로 진행할 수 있습니다.'\n",
    1269: "                      ? deliveryResolution.message || '상태를 확인하고 다시 시도해 주세요.'\n",
    1271: "                        ? '진단 결과를 기반으로 프리미엄 진단서를 자동 생성 중입니다.'\n",
    1272: "                        : '잠시 후 자동으로 진단서 생성 상태가 갱신됩니다.'\n"
}

for line_num, new_content in replacements.items():
    if line_num <= len(lines):
        lines[line_num - 1] = new_content
        print(f"Updated line {line_num}")
    else:
        print(f"Line {line_num} is out of range")

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
