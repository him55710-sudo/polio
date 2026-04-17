import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class SRIRBlock(BaseModel):
    block_id: str
    type: str = "text"
    text: str
    page_number: int
    index: int = 0
    section_label: Optional[str] = None
    parent_id: Optional[str] = None
    child_ids: List[str] = Field(default_factory=list)
    bbox: List[float] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SRIRPage(BaseModel):
    page_number: int
    width: float
    height: float
    blocks: List[SRIRBlock] = Field(default_factory=list)

class SRIRDocument(BaseModel):
    pages: List[SRIRPage] = Field(default_factory=list)
    total_pages: int = 0
    version: str = "1.0.0"

class StudentRecordIRService:
    """
    Service responsible for creating a lossless, layout-aware 
    Intermediate Representation (IR) of a student record PDF.
    """

    def create_ir(self, pdf_pages: List[Any]) -> SRIRDocument:
        """
        Converts pdfplumber page objects into a structured IR.
        
        Args:
            pdf_pages: A list of pdfplumber.Page objects.
        """
        ir_pages = []
        global_block_index = 0
        for i, page in enumerate(pdf_pages):
            page_num = page.page_number
            logger.info(f"Processing IR for page {page_num}")
            
            blocks = []
            
            # Extract words and group them into lines or blocks
            # For this "smallest real migration", we'll use pdfplumber's 
            # block-like structures or just lines.
            
            # Simple line-based block extraction for now
            lines = page.extract_text_lines()
            for j, line in enumerate(lines):
                block_id = f"blk_p{page_num}_{j}"
                blocks.append(SRIRBlock(
                    block_id=block_id,
                    text=line["text"].strip(),
                    page_number=page_num,
                    index=global_block_index,
                    bbox=[line["x0"], line["top"], line["x1"], line["bottom"]],
                    metadata={
                        "font_name": line.get("fontname"),
                        "size": line.get("size")
                    }
                ))
                global_block_index += 1
            
            ir_pages.append(SRIRPage(
                page_number=page_num,
                width=float(page.width),
                height=float(page.height),
                blocks=blocks
            ))
            
        return SRIRDocument(
            pages=ir_pages,
            total_pages=len(ir_pages)
        )
