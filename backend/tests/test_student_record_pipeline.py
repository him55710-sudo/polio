import unittest
from unittest.mock import MagicMock
from unifoli_api.services.student_record_pipeline_service import StudentRecordPipelineService
from unifoli_api.services.student_record_page_classifier_service import PageCategory

class TestStudentRecordPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = StudentRecordPipelineService()

    def test_full_pipeline_flow(self):
        # Mocking pages from pdfplumber
        mock_pages = []
        
        # Page 1: Student info
        p1 = MagicMock()
        p1.extract_text.return_value = "?™êµ?í™œê¸°ë¡ë¶€\n??ëª?: ?ê¸¸??n?ë…„?”ì¼ : 2006.01.01\n?™êµëª?: ?œêµ­ê³ ë“±?™êµ"
        mock_pages.append(p1)
        
        # Page 2: Attendance
        p2 = MagicMock()
        p2.extract_text.return_value = "ì¶œê²°?í™©\n1?™ë…„: 190??ì¶œì„"
        mock_pages.append(p2)
        
        # Page 3: Awards
        p3 = MagicMock()
        p3.extract_text.return_value = "?˜ìƒê²½ë ¥\n?˜í•™ê²½ì‹œ?€??ê¸ˆìƒ"
        p3.extract_tables.return_value = [[
            ["?˜ìƒëª?, "?±ê¸‰", "?¼ì", "ê¸°ê?", "?€??],
            ["?˜í•™ê²½ì‹œ?€??, "ê¸ˆìƒ", "2023.05.10", "?œêµ­ê³ ë“±?™êµ", "?„êµ??]
        ]]
        mock_pages.append(p3)

        # Run pipeline
        raw_text = "\n".join([p.extract_text() for p in mock_pages])
        artifact = self.pipeline.process_document(mock_pages, raw_text)

        # Assertions
        self.assertIn("canonical_data", artifact)
        self.assertIn("quality_report", artifact)
        self.assertIn("chunks", artifact)
        
        canonical = artifact["canonical_data"]
        self.assertEqual(canonical["student_name"], "?ê¸¸??)
        self.assertEqual(canonical["school_name"], "?œêµ­ê³ ë“±?™êµ")
        self.assertTrue(len(canonical["awards"]) > 0)
        self.assertEqual(canonical["awards"][0]["award_name"], "?˜í•™ê²½ì‹œ?€??)

    def test_classification_summary(self):
        p1 = MagicMock()
        p1.extract_text.return_value = "?™êµ?í™œê¸°ë¡ë¶€"
        
        summary = self.pipeline._get_classification_summary([
            SimpleNamespace(page_type=PageCategory.STUDENT_INFO),
            SimpleNamespace(page_type=PageCategory.BEHAVIOR),
        ])
        
        self.assertEqual(summary.get(PageCategory.STUDENT_INFO.value), 1)
        self.assertEqual(summary.get(PageCategory.BEHAVIOR.value), 1)

class SimpleNamespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

if __name__ == "__main__":
    unittest.main()

