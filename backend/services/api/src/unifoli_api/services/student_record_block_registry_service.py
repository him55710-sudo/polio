import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .student_record_ir_service import SRIRDocument

logger = logging.getLogger(__name__)

class AtomicBlock(BaseModel):
    id: str
    text: str
    page_number: int
    index: int = 0
    section_label: Optional[str] = None
    parent_id: Optional[str] = None
    child_ids: List[str] = Field(default_factory=list)
    source_ir_id: str
    metadata: Dict[str, Any] = {}

class StudentRecordBlockRegistry(BaseModel):
    blocks: List[AtomicBlock] = []
    total_blocks: int = 0
    document_version: str = "1.0.0"

class StudentRecordBlockRegistryService:
    """
    Service responsible for converting a structured IR into 
    a flat registry of atomic evidence blocks.
    """

    def build_registry(self, ir_doc: SRIRDocument) -> StudentRecordBlockRegistry:
        """
        Flattens the IR pages into a single registry of blocks.
        """
        registry_blocks = []
        
        for page in ir_doc.pages:
            for block in page.blocks:
                registry_blocks.append(AtomicBlock(
                    id=block.block_id,
                    text=block.text,
                    page_number=page.page_number,
                    index=block.index,
                    section_label=block.section_label,
                    parent_id=block.parent_id,
                    child_ids=block.child_ids,
                    source_ir_id=block.block_id,
                    metadata=block.metadata
                ))
                
        logger.info(f"Built block registry with {len(registry_blocks)} blocks")
        
        return StudentRecordBlockRegistry(
            blocks=registry_blocks,
            total_blocks=len(registry_blocks)
        )
