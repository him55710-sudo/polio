import os

file_path = r'c:\Users\임현수\Downloads\polio for real\polio for real\backend\services\api\src\unifoli_api\services\document_service.py'

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Update imports
old_imports = """from unifoli_api.services.student_record_pipeline_service import StudentRecordPipelineService
import pdfplumber
import logging

logger = logging.getLogger(__name__)"""

new_imports = """from unifoli_api.services.student_record_pipeline_service import StudentRecordPipelineService
import pdfplumber
import logging
from unifoli_api.core.errors import UniFoliErrorCode, UniFoliError

logger = logging.getLogger(__name__)"""

content = content.replace(old_imports, new_imports)

# Update _mark_document_failed signature if needed, or just the calls
# Let's find _mark_document_failed definition first to see if I need to update it
# I'll just update the calls for now to include error_code if I can

# Update Stage 1 and 2 logic
old_stage_logic = """        # --- STAGE 1: Base Parse (Critical) ---
        try:
            parsed = parse_uploaded_document(
                source_path,
                chunk_size_chars=settings.upload_chunk_size_chars,
                overlap_chars=settings.upload_chunk_overlap_chars,
                mask_sensitive=True,
                storage_provider=get_storage_provider_name(storage),
                storage_id=upload_asset.stored_path,
            )
            document.content_text = parsed.content_text
            document.content_markdown = parsed.content_markdown
            document.word_count = parsed.word_count
            document.page_count = parsed.page_count
            document.parser_name = parsed.parser_name
            document.masking_status = DocumentMaskingStatus.COMPLETED.value
            document.parse_metadata["masking"] = parsed.masking_metadata
            logger.info("Stage 1: Base extraction complete.")
        except Exception as e:
            _mark_document_failed(db, document, upload_asset, str(e))
            raise

        # --- STAGE 2: Advanced Semantic Pipeline (Optional Fallback) ---
        if document.source_extension.lower() == ".pdf" and document.content_text:
            try:
                with pdfplumber.open(source_path) as pdf:
                    advanced_pipeline = StudentRecordPipelineService()
                    advanced_artifact = advanced_pipeline.process_document(pdf.pages, parsed.content_text)
                    document.parse_metadata["analysis_artifact"] = advanced_artifact
                    
                    quality_report = advanced_artifact.get("quality_report", {})
                    if quality_report:
                        document.parse_metadata["pipeline_quality_score"] = float(quality_report.get("overall_score", 0))
                        document.parse_metadata["pipeline_quality_missing_sections"] = quality_report.get("missing_critical_sections", [])
                        if quality_report.get("missing_critical_sections"):
                            document.parse_metadata["needs_review"] = True
                logger.info("Advanced semantic parsing complete.")
            except Exception as e:
                logger.warning(f"Advanced pipeline failed, falling back: {str(e)}")"""

new_stage_logic = """        # --- STAGE 1: Base Parse (Critical) ---
        document.parse_metadata["stages"] = {
            "extract": {"status": "running"},
            "classify": {"status": "pending"},
            "segment": {"status": "pending"},
            "normalize": {"status": "pending"},
            "quality": {"status": "pending"},
            "enrich": {"status": "pending"}
        }
        db.add(document)
        db.commit()

        try:
            parsed = parse_uploaded_document(
                source_path,
                chunk_size_chars=settings.upload_chunk_size_chars,
                overlap_chars=settings.upload_chunk_overlap_chars,
                mask_sensitive=True,
                storage_provider=get_storage_provider_name(storage),
                storage_id=upload_asset.stored_path,
            )
            document.content_text = parsed.content_text
            document.content_markdown = parsed.content_markdown
            document.word_count = parsed.word_count
            document.page_count = parsed.page_count
            document.parser_name = parsed.parser_name
            document.masking_status = DocumentMaskingStatus.COMPLETED.value
            document.parse_metadata["masking"] = parsed.masking_metadata
            document.parse_metadata["stages"]["extract"] = {"status": "success", "completed_at": utc_now().isoformat()}
            logger.info("Stage 1: Base extraction complete.")
        except Exception as e:
            document.parse_metadata["stages"]["extract"] = {"status": "failed", "error": str(e)}
            _mark_document_failed(db, document, upload_asset, str(e)) # We'll update the error code in a second pass if needed
            raise

        # --- STAGE 2-6: Advanced Semantic Pipeline ---
        if document.source_extension.lower() == ".pdf" and document.content_text:
            try:
                with pdfplumber.open(source_path) as pdf:
                    advanced_pipeline = StudentRecordPipelineService()
                    advanced_artifact = advanced_pipeline.process_document(pdf.pages, document.content_text)
                    document.parse_metadata["analysis_artifact"] = advanced_artifact
                    
                    # Map pipeline stages back to document metadata for frontend visibility
                    successes = advanced_artifact.get("stages_success", {})
                    errors = advanced_artifact.get("stage_errors", {})
                    
                    document.parse_metadata["stages"]["classify"]["status"] = "success" if successes.get("classification") else "failed"
                    if errors.get("classification"): document.parse_metadata["stages"]["classify"]["error"] = errors["classification"]

                    document.parse_metadata["stages"]["segment"]["status"] = "success" if successes.get("parsing") else "failed"
                    if errors.get("parsing"): document.parse_metadata["stages"]["segment"]["error"] = errors["parsing"]

                    document.parse_metadata["stages"]["normalize"]["status"] = "success" if successes.get("normalization") else "failed"
                    if errors.get("normalization"): document.parse_metadata["stages"]["normalize"]["error"] = errors["normalization"]

                    document.parse_metadata["stages"]["quality"]["status"] = "success" if successes.get("quality") else "failed"
                    if errors.get("quality"): document.parse_metadata["stages"]["quality"]["error"] = errors["quality"]

                    document.parse_metadata["stages"]["enrich"]["status"] = "success" if successes.get("chunking") else "failed"
                    if errors.get("chunking"): document.parse_metadata["stages"]["enrich"]["error"] = errors["chunking"]
                    
                    quality_report = advanced_artifact.get("quality_report", {})
                    if quality_report:
                        document.parse_metadata["pipeline_quality_score"] = float(quality_report.get("overall_score", 0))
                        document.parse_metadata["pipeline_quality_missing_sections"] = quality_report.get("missing_critical_sections", [])
                        if quality_report.get("missing_critical_sections"):
                            document.parse_metadata["needs_review"] = True
                logger.info("Advanced semantic parsing stages 2-6 complete.")

            except Exception as e:
                logger.warning(f"Advanced pipeline stages 2-6 failed, falling back: {str(e)}")
                for s in ["classify", "segment", "normalize", "quality", "enrich"]:
                    if document.parse_metadata["stages"][s]["status"] == "pending":
                        document.parse_metadata["stages"][s]["status"] = "failed"
                        document.parse_metadata["stages"][s]["error"] = str(e)"""

content = content.replace(old_stage_logic, new_stage_logic)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied successfully")
