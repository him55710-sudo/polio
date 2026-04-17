import logging
from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel
from .diagnosis_axis_schema import AdmissionAxisKey

logger = logging.getLogger(__name__)

# Admissions-specific categories (Rule 8)
JudgementCategory = Literal[
    "grades",
    "club_activity",
    "subject_activity",
    "awards",
    "volunteer",
    "narrative_comment"
]

class JudgementEvidence(BaseModel):
    block_id: str
    quote: str
    page_number: int

class StudentJudgement(BaseModel):
    id: str
    claim: str
    rationale: str
    evidence: List[JudgementEvidence] = []
    confidence: float
    category: JudgementCategory
    axis_impact: List[AdmissionAxisKey] = []
    is_verified_fact: bool = True # Distinguished from inferred interpretation

class StudentRecordJudgementService:
    """
    The final layer of the full-fidelity pipeline. 
    Makes evidence-first judgements based on the full block registry 
    and link graph, mapped to admissions axes.
    """

    def generate_judgements(
        self, 
        registry: Any, 
        graph: Any, 
        target_major: Optional[str] = None
    ) -> List[StudentJudgement]:
        """
        Analyzes the record to produce evidence-backed claims.
        """
        judgements = []
        blocks = getattr(registry, "blocks", [])
        
        # Pass 1: Categorize Blocks (Smallest real migration)
        # Real implementation would use an LLM or sophisticated regex pass
        
        # Placeholder for "Subject Activity" judgement
        subject_blocks = [b for b in blocks if "세특" in b.text or "실험" in b.text or "탐구" in b.text]
        if subject_blocks:
            judgements.append(StudentJudgement(
                id="judge_subj_001",
                claim="교과 심화 탐구 역량 우수",
                rationale="다양한 교과목에서 단순 지식 습득을 넘어선 실험과 탐구 과정이 관찰됨",
                category="subject_activity",
                axis_impact=["universal_rigor", "cluster_depth"],
                evidence=[JudgementEvidence(
                    block_id=b.id,
                    quote=b.text[:50] + "...",
                    page_number=b.page_number
                ) for b in subject_blocks[:3]],
                confidence=0.9
            ))

        # Placeholder for "Club Activity" judgement
        club_blocks = [b for b in blocks if "동아리" in b.text]
        if club_blocks:
            judgements.append(StudentJudgement(
                id="judge_club_001",
                claim="자기주도적 전공 관련 동아리 활동",
                rationale="동아리 내에서 전공과 연계된 프로젝트를 주도적으로 기획하고 수행함",
                category="club_activity",
                axis_impact=["cluster_suitability", "relational_narrative"],
                evidence=[JudgementEvidence(
                    block_id=b.id,
                    quote=b.text[:50] + "...",
                    page_number=b.page_number
                ) for b in club_blocks[:3]],
                confidence=0.85
            ))
        
        logger.info(f"Generated {len(judgements)} judgements with admissions mapping")
        return judgements
