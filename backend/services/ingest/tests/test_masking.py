import pytest
import json
from unifoli_ingest.masking import StudentLifeRecordRedactor, process_student_record

def test_hard_redactions():
    sample = "?±ëª…: ê¹€ì² ìˆ˜, ì£¼ë??±ë¡ë²ˆí˜¸: 060101-3123456, ?°ë½ì²? 010-1234-5678"
    result = process_student_record(sample)
    
    assert "[?™ìƒëª?" in result["redacted_text"]
    assert "[ì£¼ë??±ë¡ë²ˆí˜¸]" in result["redacted_text"]
    assert "[PHONE_MASKED]" in result["redacted_text"]
    assert "ê¹€ì² ìˆ˜" not in result["redacted_text"]
    assert "060101-3123456" not in result["redacted_text"]

def test_date_generalization():
    redactor = StudentLifeRecordRedactor()
    
    # 1st Semester (March)
    res1 = redactor.redact("2024.03.15")
    assert "2024?™ë…„??1?™ê¸°" in res1["redacted_text"]
    
    # 2nd Semester (October)
    res2 = redactor.redact("2024.10.10")
    assert "2024?™ë…„??2?™ê¸°" in res2["redacted_text"]
    
    # 2nd Semester (January next year - belongs to prev academic year)
    res3 = redactor.redact("2025.01.20")
    assert "2024?™ë…„??2?™ê¸°" in res3["redacted_text"]

def test_school_generalization():
    sample = "?œìš¸ê³¼í•™ê³ ë“±?™êµ ì¡¸ì—… ???œêµ­?€?™êµ ì§„í•™"
    result = process_student_record(sample)
    
    assert "[ê³ ë“±?™êµ]" in result["redacted_text"]
    assert "?œìš¸ê³¼í•™ê³ ë“±?™êµ" not in result["redacted_text"]

def test_preservation_of_academic_data():
    sample = "[?±ì ?? êµ?–´: ?ì ??95, ?ì°¨?±ê¸‰ 1. [?¸ë??¥ë ¥] ê¸°í›„ë³€???êµ¬ ?˜í–‰."
    result = process_student_record(sample)
    
    assert "95" in result["redacted_text"]
    assert "?ì°¨?±ê¸‰ 1" in result["redacted_text"]
    assert "ê¸°í›„ë³€???êµ¬" in result["redacted_text"]

def test_footer_removal():
    sample = "ë³¸ë¬¸ ?´ìš©\n?œìš¸ê³ ë“±?™êµ 2024.05.15 1 / 15 ?˜ì´ì§€\n?¤ìŒ ë³¸ë¬¸"
    result = process_student_record(sample)
    
    assert "?œìš¸ê³ ë“±?™êµ" not in result["redacted_text"]
    assert "?˜ì´ì§€" not in result["redacted_text"]
    assert "ë³¸ë¬¸ ?´ìš©" in result["redacted_text"]
    assert "?¤ìŒ ë³¸ë¬¸" in result["redacted_text"]

def test_redaction_report_structure():
    sample = "?±ëª…: ê¹€ì² ìˆ˜, ì£¼ì†Œ: ?œìš¸??ê°•ë‚¨êµ?
    result = process_student_record(sample)
    
    assert "redacted_text" in result
    assert "redaction_report" in result
    assert "review_flags" in result
    assert "hard_redactions" in result["redaction_report"]
    assert len(result["redaction_report"]["hard_redactions"]) > 0

if __name__ == "__main__":
    # If running as a script, just execute one to see output
    res = process_student_record("?´ë¦„: ?´ì˜?? ì£¼ë?ë²ˆí˜¸: 070202-4567890")
    print(json.dumps(res, indent=2, ensure_ascii=False))
