import os

file_path = r'c:\Users\임현수\Downloads\polio for real\polio for real\frontend\src\pages\Workshop.tsx'

with open(file_path, 'rb') as f:
    content = f.read()

# Known Moijbake patterns and their corrections
replacements = [
    (b'\xeb\xb9\xa0\xeb\xa5\xb8 \xec\x9d\x91\xeb\x8b\xb5', '빠른 응답'), # This might not work if it's already double-encoded
]

# Let's try to decode as cp949 and encode as utf8 if it was saved as cp949
try:
    decoded = content.decode('utf-8')
    # If it decodes as utf-8 but looks like nonsense, it's Mojibake (double encoded or wrong source)
    # The problematic strings look like they were UTF-8 bytes interpreted as CP949 and then saved as UTF-8.
    
    # Common Mojibake fix: content.encode('iso-8859-1').decode('utf-8') or similar
    # But here they look like they were already corrupted.
    
    # I'll just do a string replacement for the specific line contents I saw.
    
    lines = decoded.splitlines()
    new_lines = []
    for line in lines:
        # replace '鍮좊Ⅸ ?묐떟' with '빠른 응답'
        line = line.replace('鍮좊Ⅸ ?묐떟', '빠른 응답')
        line = line.replace('洹좏삎 紐⑤뱶', '균형 모드')
        line = line.replace('?ы솕 紐⑤뱶', '심화 모드')
        line = line.replace('?덈뀞?섏꽭?? ?대뼡 二쇱젣??蹂닿퀬?쒕? ?⑤낵源뚯슂?', '안녕하세요? 어떤 주제의 보고서를 써볼까요?')
        line = line.replace('?붿껌?섏떊', '요청하신')
        line = line.replace('諛⑺뼢???쒖븞?쒕┰?덈떎', '방향을 제안드립니다')
        line = line.replace('?곹빀 ?댁쑀', '적합 이유')
        line = line.replace('湲곕줉 ?곌껐', '기록 연결')
        line = line.replace('紐⑺몴 ?곌껐', '목표 연결')
        line = line.replace('二쇱쓽', '주의')
        line = line.replace('李멸퀬', '참고')
        line = line.replace('?꾨옒 移대뱶?먯꽌 ??媛€吏€瑜??좏깮??二쇱꽭??', '아래 카드에서 한 가지를 선택해 주세요.')
        line = line.replace('?좏깮?섏떊 二쇱젣??', '선택하신 주제는')
        line = line.replace('?낅땲??', '입니다.')
        line = line.replace('沅뚯옣 遺꾨웾', '권장 분량')
        line = line.replace('沅뚯옣 媛쒖슂', '권장 개요')
        line = line.replace('?ㅻⅨ履?珥덉븞 ?⑤꼸???ㅽ???珥덉븞??梨꾩썙 ?먯뿀?듬땲??', '오른쪽 초안 패널에 스타터 초안을 채워 두었습니다.')
        line = line.replace('?ㅼ쓬 硫붿떆吏€濡??몃? 臾몃떒???댁뼱媛€ 蹂댁꽭??', '다음 메시지로 세부 문단을 이어가 보세요.')
        line = line.replace('Uni Foli媛€ ?묒꽦 以?..', 'Uni Foli가 작성 중..')
        line = line.replace('?좏깮??二쇱젣濡?珥덉븞 ?몄뀡??以€鍮?以묒엯?덈떎...', '선택한 주제로 초안 섹션을 준비 중입니다...')
        line = line.replace('?대┃?섎㈃ ?뚰겕??珥덉븞??利됱떆 ?앹꽦?⑸땲??', '클릭하면 워크샵 초안이 즉시 생성됩니다.')
        line = line.replace('?€?λ맂 二쇱젣', '저장된 주제')
        line = line.replace('珥덉븞??遺덈윭?붿뒿?덈떎', '초안을 불러왔습니다')
        line = line.replace('?댁뼱??蹂닿컯??蹂댁꽭??', '이어서 보강해 보세요.')
        line = line.replace('?뚰겕?띿쓣 遺덈윭?ㅼ? 紐삵뻽?듬땲??', '워크샵을 불러오지 못했습니다.')
        line = line.replace('濡쒖뺄 紐⑤뱶濡??꾪솚?⑸땲??', '로컬 모드로 전환합니다.')
        line = line.replace('?몄뀡 ?곌껐???ㅽ뙣?덉뒿?덈떎', '세션 연결에 실패했습니다.')
        line = line.replace('濡쒖뺄?먯꽌 珥덉븞 ?묒꽦??吏꾪뻾?섏떎 ???덉뒿?덈떎.', '로컬에서 초안 작성을 진행하실 수 있습니다.')
        line = line.replace('Uni Foli媛€ ?쒖븞???댁슜??諛뷀깢?쇰줈 援ъ꽦??臾몄꽌?낅땲??', 'Uni Foli가 제안한 내용을 바탕으로 구성된 문서입니다.')
        line = line.replace('二쇱젣 湲곗??쇰줈 3媛€吏€', '주제 기준으로 3가지')
        line = line.replace('?꾨옒 移대뱶?먯꽌 ??媛€吏€瑜??좏깮??二쇱꽭??', '아래 카드에서 한 가지를 선택해 주세요.')
        line = line.replace('?ㅼ쓬 硫붿떆吏€濡??몃? 臾몃떒???댁뼱媛€ 蹂댁꽭??', '다음 메시지로 세부 문단을 이어가 보세요.')
        line = line.replace('?ㅽ???珥덉븞??梨꾩썙 ?먯뿀?듬땲??', '스타터 초안을 채워 두었습니다.')
        
        new_lines.append(line)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    print("Success")
except Exception as e:
    print(f"Error: {e}")
