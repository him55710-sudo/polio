# -*- coding: utf-8 -*-
from typing import TypedDict, List

class TopicExample(TypedDict):
    id: str
    label: str
    suggestion_type: str
    reason: str

# 고품질 탐구 주제 라이브러리 (1000+ 주제 지향)
TOPIC_LIBRARY: List[TopicExample] = [
    # [관심사 기반]
    {"id": "int-game-001", "label": "리그 오브 레전드 캐릭터 밸런싱의 통계학적 분석", "suggestion_type": "interest", "reason": "평소 즐기는 게임의 밸런스 패치 원리를 수학적으로 탐구해보는 건 어떨까요?"},
    {"id": "int-music-001", "label": "K-Pop 안무의 기하학적 패턴과 공간 활용 연구", "suggestion_type": "interest", "reason": "좋아하는 음악과 춤 속에 숨겨진 수학적 미학을 찾아보세요."},
    {"id": "int-env-001", "label": "제로 웨이스트 카페의 탄소 저감 효과 시뮬레이션", "suggestion_type": "interest", "reason": "환경에 대한 관심을 실천적인 데이터로 증명할 수 있습니다."},
    {"id": "int-ai-001", "label": "생성형 AI를 활용한 나만의 웹툰 스토리보드 제작 자동화", "suggestion_type": "interest", "reason": "최신 기술을 좋아하는 창작 활동에 결합해보세요."},
    
    # [교과 심화 - 수학]
    {"id": "sub-math-001", "label": "미분 방정식을 이용한 전염병 확산 모델(SIR) 분석", "suggestion_type": "subject", "reason": "수학 시간에 배운 미분이 사회 문제를 해결하는 강력한 도구가 됩니다."},
    {"id": "sub-math-002", "label": "푸리에 급수를 활용한 악기 음색의 파형 분석", "suggestion_type": "subject", "reason": "소리라는 파동을 수학적으로 분해하여 예술과 과학을 연결합니다."},
    
    # [교과 심화 - 과학]
    {"id": "sub-sci-001", "label": "천연 고분자 물질을 이용한 친환경 생분해성 플라스틱 제작 실험", "suggestion_type": "subject", "reason": "화학적 원리를 이용해 지구를 구하는 기술을 제안해보세요."},
    {"id": "sub-sci-002", "label": "크리스퍼 유전자 가위의 윤리적 쟁점과 생명공학적 한계", "suggestion_type": "subject", "reason": "생명과학의 최첨단 기술을 인문학적 관점에서 비판적으로 고찰합니다."},
    
    # [학과 융합 - 경영/IT]
    {"id": "maj-biz-001", "label": "빅데이터 분석을 통한 지역 상권 젠트리피케이션 예측 모델", "suggestion_type": "major", "reason": "경영적 감각과 데이터 과학 기술을 융합한 실천적 연구입니다."},
    {"id": "maj-med-001", "label": "웨어러블 기기를 활용한 청소년 수면 패턴과 학습 효율의 상관관계", "suggestion_type": "major", "reason": "의학적 관심사를 IT 기술과 통계로 풀어내어 설득력을 높입니다."},

    # ... (중략: 실제 구현 시 1000개 수준의 데이터가 이곳에 포함됨)
]

# 실제 서비스에서는 이 데이터를 바탕으로 사용자 맞춤형 샘플링을 수행합니다.
def get_library_recommendations(subject: str, limit: int = 5) -> List[TopicExample]:
    # 간단한 키워드 매칭 로직 (실제로는 더 복잡한 벡터 검색 가능)
    matches = [t for t in TOPIC_LIBRARY if subject in t['label'] or subject in t['reason']]
    return matches[:limit] if matches else TOPIC_LIBRARY[:limit]
