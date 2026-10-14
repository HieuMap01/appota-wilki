"""
Quick end-to-end LLM test with proper Vietnamese queries.
Run: python src/quick_llm_test.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline import run_pipeline, USER_PROFILES

TESTS = [
    ("Nhân viên Gamota (Nguyễn Văn A)", "Tôi được nghỉ bao nhiêu ngày phép mỗi năm?"),
    ("Nhân viên Appota Pay (Trần Thị B)", "Tôi được nghỉ bao nhiêu ngày phép mỗi năm?"),
    ("Nhân viên Gamota (Nguyễn Văn A)", "Quy trình onboarding nhân viên mới như thế nào?"),
]

for profile_key, query in TESTS:
    ctx = USER_PROFILES[profile_key]
    print(f"\n{'='*60}")
    print(f"[{profile_key}]")
    print(f"Hoi: {query}")
    r = run_pipeline(query, ctx)
    print(f"chunks_used: {r['chunks_used']} | no_data: {r['no_data']}")
    print(f"Sources: {[s.get('doc_id') for s in r['sources']]}")
    print(f"\nTra loi:\n{r['answer']}")
