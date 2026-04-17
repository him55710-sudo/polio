import logging
from typing import Dict, List, Set, Any
from pydantic import BaseModel
from .student_record_block_registry_service import StudentRecordBlockRegistry

logger = logging.getLogger(__name__)

class CoverageReport(BaseModel):
    total_blocks: int
    covered_blocks: int
    coverage_percentage: float
    missing_block_ids: List[str]
    metadata: Dict[str, Any] = {}

class StudentRecordAuditService:
    """
    Service responsible for auditing the pipeline to ensure 
    full-fidelity coverage of all evidence blocks.
    """

    def generate_coverage_audit(
        self, 
        registry: StudentRecordBlockRegistry, 
        covered_block_ids: Set[str]
    ) -> CoverageReport:
        """
        Compares the total blocks in registry with the blocks 
        that were actually referenced or processed.
        """
        total_blocks = registry.total_blocks
        actual_covered = [bid for bid in covered_block_ids if any(b.id == bid for b in registry.blocks)]
        covered_count = len(actual_covered)
        
        missing_ids = [b.id for b in registry.blocks if b.id not in covered_block_ids]
        
        coverage_pct = (covered_count / total_blocks * 100.0) if total_blocks > 0 else 100.0
        
        logger.info(f"Fidelity Audit: {covered_count}/{total_blocks} blocks covered ({coverage_pct:.1f}%)")
        
        return CoverageReport(
            total_blocks=total_blocks,
            covered_blocks=covered_count,
            coverage_percentage=coverage_pct,
            missing_block_ids=missing_ids
        )
