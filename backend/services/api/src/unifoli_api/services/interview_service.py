import logging
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from unifoli_api.core.llm import get_llm_client, resolve_llm_runtime
from unifoli_api.services.prompt_registry import get_prompt_registry
from unifoli_api.services.diagnosis_service import DiagnosisResult

logger = logging.getLogger(__name__)

class InterviewQuestion(BaseModel):
    id: str
    question: str
    rationale: str
    expected_evidence_ids: List[str] = Field(default_factory=list)

class InterviewEvaluation(BaseModel):
    score: int = Field(ge=0, le=100)
    axes_scores: dict[str, int] = Field(default_factory=dict)
    feedback: str
    coaching_advice: str

class InterviewService:
    async def generate_questions(self, diagnosis: DiagnosisResult) -> List[InterviewQuestion]:
        """
        Generates interview questions based on the diagnosis result and evidence.
        """
        # Minimal implementation for Phase 1
        # In a real scenario, this would call an LLM with a specific prompt.
        # For now, we simulate with a few logical candidates.
        
        questions = [
            InterviewQuestion(
                id="q1",
                question=f"{diagnosis.record_completion_state == 'finalized' and '생활기록부의 강점인 ' or ''}{diagnosis.strengths[0] if diagnosis.strengths else '지원 전공'}과 관련하여 본인이 가장 깊이 있게 탐구한 내용은 무엇인가요?",
                rationale="가장 뚜렷한 강점 요소를 기반으로 진정성과 구체성을 확인하기 위함입니다."
            ),
            InterviewQuestion(
                id="q2",
                question="탐구 과정에서 가장 큰 어려움은 무엇이었으며, 이를 인용된 근거를 바탕으로 어떻게 해결했는지 설명해 주세요.",
                rationale="문제 해결 능력과 성찰의 깊이를 파악하기 위함입니다."
            )
        ]
        return questions

    async def evaluate_answer(self, question: str, answer: str, context: str) -> InterviewEvaluation:
        """
        Evaluates the student's answer based on the 4 axes.
        """
        # This will call the LLM in Phase 2. 
        # For Phase 1, we provide a structured placeholder response logic.
        
        # Simulating evaluation axes
        evaluation = InterviewEvaluation(
            score=75,
            axes_scores={
                "구체성": 80,
                "진정성": 70,
                "학생부 근거 활용": 65,
                "전공 연결성": 85
            },
            feedback="답변에서 전공에 대한 열의는 잘 드러나 있으나, 생활기록부의 구체적인 활동 내용을 수치나 명칭으로 더 강조하면 좋겠습니다.",
            coaching_advice="본인의 활동 중 '...' 섹션에 언급된 '...' 키워드를 답변 전반에 녹여보세요."
        )
        return evaluation
