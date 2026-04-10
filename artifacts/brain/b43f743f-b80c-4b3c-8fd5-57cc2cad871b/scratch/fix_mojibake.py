import os

file_path = r'c:\Users\임현수\Downloads\polio for real\polio for real\frontend\src\pages\Diagnosis.tsx'

replacements = {
    "admission_type: goals.admission_type || '?숈깮遺€醫낇빀',": "admission_type: goals.admission_type || '학생부종합',",
    "toast.success('紐⑺몴媛€ ?€?λ릺?덉뒿?덈떎.');": "toast.success('목표가 저장되었습니다.');",
    "getApiErrorMessage(error, '?€?λ맂 ?낅줈??湲곕줉?쇰줈 吏꾨떒???쒖옉?섏? 紐삵뻽?댁슂.');": "getApiErrorMessage(error, '저장된 업로드 기록으로 진단을 시작하지 못했어요.');",
    "toast.loading('PDF ?낅줈?쒖? 吏꾨떒 以€鍮꾨? 吏꾪뻾 以묒엯?덈떎...');": "toast.loading('PDF 업로드와 진단 준비를 진행 중입니다...');",
    "const emptyContentError = 'PDF?먯꽌 吏꾨떒 媛€?ν븳 ?띿뒪?몃? 李얠? 紐삵뻽?듬땲?? OCR ?덉쭏????醫뗭? ?뚯씪濡??ㅼ떆 ?쒕룄??二쇱꽭??';": "const emptyContentError = 'PDF에서 진단 가능한 텍스트를 찾지 못했습니다. OCR 품질이 더 좋은 파일로 다시 시도해 주세요.';",
    "const parseNote = parsedDocument.page_count ? `?뚯떛 ?꾨즺 (${parsedDocument.page_count}?섏씠吏€)` : '?뚯떛 ?꾨즺';": "const parseNote = parsedDocument.page_count ? `파싱 완료 (${parsedDocument.page_count}페이지)` : '파싱 완료';",
    "label: '紐⑺몴 ?ㅼ젙',": "label: '목표 설정',",
    "description: '吏€??紐⑺몴 ?뺤젙',": "description: '지원 목표 확정',",
    "description: '?숈깮遺€ PDF ?쒖텧',": "description: '학생부 PDF 제출',",
    "step === 'GOALS' ? '紐⑺몴媛€ 遺꾨챸?좎닔濡?吏꾨떒 寃곌낵?€ ?섏뒪??異붿쿇???뺥솗?꾧? ?믪븘吏묐땲??' :": "step === 'GOALS' ? '목표가 분명할수록 진단 결과와 워크숍 추천의 정확도가 높아집니다.' :",
    "step === 'UPLOAD' ? 'PDF 1媛쒕? ?낅줈?쒗븯硫??뚯떛, 留덉뒪?? 吏꾨떒???쒖감?곸쑝濡?吏꾪뻾?⑸땲??' :": "step === 'UPLOAD' ? 'PDF 1개를 업로드하면 파싱, 마스킹, 진단이 순차적으로 진행됩니다.' :",
    "step === 'ANALYSING' ? '洹쇨굅 留ㅽ븨怨??꾪뿕 ?좏샇 遺꾩꽍??吏꾪뻾 以묒엯?덈떎.' :": "step === 'ANALYSING' ? '근거 매핑과 위험 신호 분석을 진행 중입니다.' :",
    "step === 'RESULT' ? '媛뺤젏, 蹂댁셿?? ?≪뀡 ?뚮옖???뺤씤?????뚰겕?띿쑝濡??대룞?섏꽭??' :": "step === 'RESULT' ? '강점, 보완점, 액션 플랜을 확인한 후 워크숍으로 이동하세요.' :",
    "'?ㅽ뙣 ?먯씤怨??묒뾽 ?곹깭瑜??뺤씤?섍퀬 ?덉쟾?섍쾶 ?ъ떆?꾪빐 二쇱꽭??';": "'실패 원인과 작업 상태를 확인하고 안전하게 다시 시도해 주세요.';",
    "title=\"吏꾨떒 吏꾪뻾 ?€?꾪뀒?대툝\"": "title=\"진단 진행 타임라인\"",
    "description=\"?덉긽 ?뚯슂?쒓컙 ?€鍮??꾩옱 吏꾨떒 吏꾪뻾瑜좎쓣 蹂댁뿬?쒕젮??\"": "description=\"예상 소요 시간 대비 현재 진단 진행률을 보여드려요\"",
    "title=\"吏€??紐⑺몴 紐⑸줉\"": "title=\"지원 목표 목록\"",
    "description=\"泥?踰덉㎏ 紐⑺몴媛€ 吏꾨떒 湲곗??먯쑝濡??ъ슜?⑸땲??\"": "description=\"첫 번째 목표가 진단 기준점으로 사용됩니다\"",
    "EmptyState title=\"?ㅼ젙??紐⑺몴媛€ ?놁뒿?덈떎\" description=\"吏꾨떒???쒖옉?섎젮硫?理쒖냼 1媛쒖쓽 紐⑺몴瑜??ㅼ젙??二쇱꽭??\"": "EmptyState title=\"설정한 목표가 없습니다\" description=\"진단을 시작하려면 최소 1개의 목표를 설정해 주세요\"",
    "紐⑺몴 ?€??": "목표 저장",
    "?숈깮遺€ PDF瑜??쒕옒洹명븯嫄곕굹 ?대┃???낅줈?쒗븯?몄슂": "학생부 PDF를 드래그하거나 클릭하여 업로드하세요",
    "?낅줈???꾩뿉???섏씠吏€瑜??좎??섎㈃ ?먮룞?쇰줈 ?곹깭媛€ 媛깆떊?⑸땲??": "업로드 이후에 페이지를 유지하면 자동으로 상태가 갱신됩니다",
    "title=\"臾몄꽌 遺꾩꽍怨?吏꾨떒 ?앹꽦??吏꾪뻾 以묒엯?덈떎\"": "title=\"문서 분석과 진단 생성을 진행 중입니다\"",
    "description=\"?뚯떛???앸굹硫??먮룞?쇰줈 吏꾨떒 ?앹꽦 ?④퀎濡??섏뼱媛€硫? ?섏씠吏€瑜??좎??섎㈃ ?곹깭媛€ ?먮룞 媛깆떊?⑸땲??\"": "description=\"파싱이 끝나면 자동으로 진단 생성 단계로 넘어가며, 페이지를 유지하면 상태가 자동 갱신됩니다\"",
    "?낅줈?쒕줈 ?뚯븘媛€湲?": "업로드로 돌아가기",
    "?꾨Ц 吏꾨떒?쒓? 以€鍮꾨릺?덉뒿?덈떎": "전문 진단서가 준비되었습니다",
    "吏꾨떒 ?④퀎?먯꽌 臾몄젣媛€ 諛쒖깮?덉뒿?덈떎": "진단 단계에서 문제가 발생했습니다",
    "吏꾨떒???앹꽦 ?④퀎?먯꽌 臾몄젣媛€ 諛쒖깮?덉뒿?덈떎": "진단서 생성 단계에서 문제가 발생했습니다",
    "?꾨Ц 吏꾨떒?쒕? ?앹꽦?섍퀬 ?덉쒿?덈떎": "전문 진단서를 생성하고 있습니다",
    "?꾨옒?먯꽌 誘몃━蹂닿린?€ PDF ?ㅼ슫濡쒕뱶瑜?諛붾줈 吏꾪뻾?????덉뒿?덈떎.": "아래에서 미리보기와 PDF 다운로드를 바로 진행할 수 있습니다.",
    "?곹깭瑜??뺤씤?????ㅼ떆 ?쒕룣??二쇱꽭??": "상태를 확인하고 다시 시도해 주세요.",
    "吏꾨떒 寃곌낵瑜?湲곕컲?쇰줈 premium_10p 吏꾨떒?쒕? ?먮룞 ?앹꽦 以묒엯?덈떎.": "진단 결과를 기반으로 프리미엄 진단서를 자동 생성 중입니다.",
    "?좎떆 ???먮룞?쇰줈 吏꾨떒???앹꽦 ?곹깭媛€ 媛깆떊?⑸땲??": "잠시 후 자동으로 진단서 생성 상태가 갱신됩니다.",
    "??{action}": "• {action}" # Fixed bullet point characters
}

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

for old_val, new_val in replacements.items():
    if old_val in content:
        content = content.replace(old_val, new_val)
        print(f"Replaced: {old_val[:20]}...")
    else:
        print(f"NOT FOUND: {old_val[:20]}...")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
