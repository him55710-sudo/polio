import logging
from typing import Dict, List, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    relation_type: str  # e.g., "sequential", "thematic", "category_match"
    weight: float = 1.0

class StudentRecordLinkGraph(BaseModel):
    edges: List[GraphEdge] = []
    metadata: Dict[str, Any] = {}

class StudentRecordLinkGraphService:
    """
    Service responsible for building a graph of relationships 
    between document blocks, sections, and facts.
    """

    def build_graph(self, blocks: List[Any], facts: List[Any]) -> StudentRecordLinkGraph:
        """
        Builds cross-links between related information units.
        """
        edges = []
        
        # 1. Sequential Linking
        for i in range(len(blocks) - 1):
            edges.append(GraphEdge(
                source_id=blocks[i].id,
                target_id=blocks[i+1].id,
                relation_type="sequential"
            ))
            
        # 2. Category-based Thematic Linking (Smallest real migration)
        # If two blocks share high-frequency keywords, link them.
        for i in range(len(blocks)):
            for j in range(i + 1, min(i + 20, len(blocks))): # Limited window for performance
                b1 = blocks[i]
                b2 = blocks[j]
                
                # Check for shared specific terms (e.g. subject names)
                # This is a placeholder for a real semantic linker.
                common_terms = {"수학", "과학", "물리", "AI", "프로그래밍", "봉사", "리더십"}
                for term in common_terms:
                    if term in b1.text and term in b2.text:
                        edges.append(GraphEdge(
                            source_id=b1.id,
                            target_id=b2.id,
                            relation_type="thematic",
                            weight=0.5
                        ))
        
        logger.info(f"Built link graph with {len(edges)} edges")
        return StudentRecordLinkGraph(edges=edges)
