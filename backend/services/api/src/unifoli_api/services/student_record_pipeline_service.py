import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from .student_record_page_classifier_service import StudentRecordPageClassifierService
from .student_record_section_parser_service import StudentRecordSectionParserService
from .student_record_normalizer_service import StudentRecordNormalizerService
from .student_record_quality_service import StudentRecordQualityService
from .student_record_chunking_service import StudentRecordChunkingService

logger = logging.getLogger(__name__)

class StudentAnalysisArtifact(BaseModel):
    """
    The canonical output of the semantic parsing pipeline.
    This artifact is stored in ParsedDocument.parse_metadata["analysis_artifact"].
    """
    canonical_data: Optional[Dict[str, Any]] = None  # StudentRecordCanonicalSchema as dict
    quality_report: Optional[Dict[str, Any]] = None
    chunks: Optional[List[Dict[str, Any]]] = None
    version: str = "2.1.0"
    parsing_metadata: Dict[str, Any]
    stages_success: Dict[str, bool] = {}
    stage_errors: Dict[str, str] = {}

class StudentRecordPipelineService:
    """
    Orchestrator for the advanced student record parsing pipeline.
    This service replaces the simple text extraction with a structured,
    layout-aware semantic parsing flow.
    """

    def __init__(self):
        self.classifier = StudentRecordPageClassifierService()
        self.parser = StudentRecordSectionParserService()
        self.normalizer = StudentRecordNormalizerService()
        self.quality_service = StudentRecordQualityService()
        self.chunker = StudentRecordChunkingService()

    def process_document(self, pages: List[Any], raw_text: str) -> Dict[str, Any]:
        """
        Runs the full semantic parsing pipeline.
        
        Args:
            pages: List of page objects from pdfplumber extraction.
            raw_text: Full concatenated text of the document.
            
        Returns:
            A dictionary equivalent to StudentAnalysisArtifact.
        """
        stages_success = {
            "classification": False,
            "parsing": False,
            "normalization": False,
            "quality": False,
            "chunking": False
        }
        stage_errors = {}
        
        canonical_data = None
        quality_report = None
        chunks = []
        sections = []
        classified_pages = []

        logger.info(f"Starting semantic parsing pipeline for document with {len(pages)} pages")

        # 1. Page Classification
        try:
            classified_pages = self.classifier.classify_pages(pages)
            stages_success["classification"] = True
            logger.info("Step 1: Page classification complete")
        except Exception as e:
            stage_errors["classification"] = str(e)
            logger.error(f"Step 1 Failed: {str(e)}")

        # 2. Section Parsing (Segmentation)
        if stages_success["classification"]:
            try:
                sections = self.parser.parse_sections(classified_pages)
                stages_success["parsing"] = True
                logger.info(f"Step 2: Section parsing complete. Found {len(sections)} sections.")
            except Exception as e:
                stage_errors["parsing"] = str(e)
                logger.error(f"Step 2 Failed: {str(e)}")

        # 3. Data Normalization
        if stages_success["parsing"]:
            try:
                canonical_data_obj = self.normalizer.normalize_sections(sections)
                canonical_data = canonical_data_obj.dict() if hasattr(canonical_data_obj, 'dict') else canonical_data_obj
                stages_success["normalization"] = True
                logger.info("Step 3: Normalization complete")
            except Exception as e:
                stage_errors["normalization"] = str(e)
                logger.error(f"Step 3 Failed: {str(e)}")

        # 4. Quality Control
        if stages_success["normalization"]:
            try:
                quality_report = self.quality_service.evaluate_quality(canonical_data_obj if 'canonical_data_obj' in locals() else canonical_data, sections)
                stages_success["quality"] = True
                logger.info(f"Step 4: Quality evaluation complete. Score: {quality_report.get('overall_score')}")
            except Exception as e:
                stage_errors["quality"] = str(e)
                logger.error(f"Step 4 Failed: {str(e)}")

        # 5. Semantic Chunking
        if stages_success["normalization"]: # We can chunk even if quality check fails
            try:
                chunks = self.chunker.create_chunks(canonical_data_obj if 'canonical_data_obj' in locals() else canonical_data)
                stages_success["chunking"] = True
                logger.info(f"Step 5: Semantic chunking complete. Generated {len(chunks)} chunks.")
            except Exception as e:
                stage_errors["chunking"] = str(e)
                logger.error(f"Step 5 Failed: {str(e)}")

        # Construct final artifact
        artifact = StudentAnalysisArtifact(
            canonical_data=canonical_data,
            quality_report=quality_report,
            chunks=chunks,
            stages_success=stages_success,
            stage_errors=stage_errors,
            parsing_metadata={
                "page_count": len(pages),
                "section_count": len(sections),
                "classification_summary": self._get_classification_summary(classified_pages) if classified_pages else {}
            }
        )

        return artifact.dict()

    def _get_classification_summary(self, classified_pages: List[Any]) -> Dict[str, int]:
        summary = {}
        for p in classified_pages:
            ptype = p.page_type.value if hasattr(p, 'page_type') else "unknown"
            summary[ptype] = summary.get(ptype, 0) + 1
        return summary
