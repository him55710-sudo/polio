import json
import os
import re
from typing import List, Dict, Any, Set

# vector_service의 로직을 참고하여 어휘적 유사도 계산 유틸리티 구현
TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)
STOPWORDS = {"의", "를", "가", "이", "은", "는", "에", "와", "과", "도", "에서", "보다", "부터", "까지"}

def extract_terms(text: str) -> Set[str]:
    """텍스트에서 의미 있는 단어 집합을 추출합니다."""
    return {
        token.lower()
        for token in TOKEN_PATTERN.findall(text or "")
        if token.lower() not in STOPWORDS and len(token) > 1
    }

def calculate_similarity(query_terms: Set[str], target_terms: Set[str]) -> float:
    """어휘적 겹침 정도를 계산합니다."""
    if not query_terms or not target_terms:
        return 0.0
    overlap = len(query_terms & target_terms)
    return overlap / len(query_terms)

class TopicSearchService:
    def __init__(self, pool_path: str = None):
        if pool_path is None:
            pool_path = os.path.join(os.path.dirname(__file__), "topics_pool.json")
        
        self.pool: List[Dict[str, Any]] = []
        if os.path.exists(pool_path):
            try:
                with open(pool_path, "r", encoding="utf-8") as f:
                    self.pool = json.load(f)
                # 성능을 위해 미리 토큰화
                for item in self.pool:
                    item["_terms"] = extract_terms(item["label"] + " " + item["reason"])
            except Exception as e:
                print(f"Failed to load topics pool: {e}")

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """쿼리와 가장 관련 있는 주제를 검색합니다."""
        query_terms = extract_terms(query)
        if not query_terms or not self.pool:
            return self.pool[:limit]

        scored_items = []
        for item in self.pool:
            base_score = calculate_similarity(query_terms, item["_terms"])
            
            # 학과명 가중치 부여: 쿼리에 포함된 단어가 주제 레이블에 직접 포함되어 있으면 가중치
            bonus = 0.0
            for term in query_terms:
                if term in item["label"]:
                    bonus += 0.5 # 학과명이나 핵심 단어가 겹치면 큰 가산점
            
            total_score = base_score + bonus
            if total_score > 0:
                scored_items.append((total_score, item))
        
        # 점수 순으로 정렬
        scored_items.sort(key=lambda x: x[0], reverse=True)
        
        # 결과 추출 및 중복 제거
        results = []
        seen_labels = set()
        for _, item in scored_items:
            if item["label"] not in seen_labels:
                results.append(item)
                seen_labels.add(item["label"])
            if len(results) >= limit:
                break
        
        # 검색 결과가 부족하면 일반적인 주제로 채움
        if len(results) < limit:
            remaining = limit - len(results)
            for item in self.pool:
                if item["label"] not in seen_labels:
                    results.append(item)
                    seen_labels.add(item["label"])
                    remaining -= 1
                if remaining <= 0:
                    break
                    
        return results

# 싱글톤 인스턴스
_topic_search_service = None

def get_topic_search_service() -> TopicSearchService:
    global _topic_search_service
    if _topic_search_service is None:
        _topic_search_service = TopicSearchService()
    return _topic_search_service
