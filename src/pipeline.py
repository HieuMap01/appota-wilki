"""
Main RAG pipeline orchestrator.
Combines: Identity → Filter → Retrieve → Score → Generate
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from retriever import retrieve
from llm import generate_answer, detect_conflict

# ── User profiles for demo (mock identity) ────────────────────────
USER_PROFILES = {
    "Nhân viên Gamota (Nguyễn Văn A)": {
        "user_name": "Nguyễn Văn A",
        "don_vi":    "gamota",
        "cap_bac":   "nhan_vien",
    },
    "Nhân viên Appota Pay (Trần Thị B)": {
        "user_name": "Trần Thị B",
        "don_vi":    "appota_pay",
        "cap_bac":   "nhan_vien",
    },
    "Team Lead Gamota (Lê Văn C)": {
        "user_name": "Lê Văn C",
        "don_vi":    "gamota",
        "cap_bac":   "team_lead",
    },
    "Manager HR Tập đoàn (Phạm Thị D)": {
        "user_name": "Phạm Thị D",
        "don_vi":    "hr_dept",
        "cap_bac":   "manager",
    },
    "Nhân viên Tập đoàn (Hoàng Văn E)": {
        "user_name": "Hoàng Văn E",
        "don_vi":    "tap_doan",
        "cap_bac":   "nhan_vien",
    },
}


def run_pipeline(query: str, user_context: dict) -> dict:
    """
    Full RAG pipeline:
      1. Retrieve relevant chunks with permission filter
      2. Detect conflicts
      3. Generate answer with LLM guardrails

    Returns dict with:
      - answer        : str (final response to user)
      - sources       : list of source metadata
      - debug_info    : retrieval diagnostics
      - chunks_used   : number of chunks used
      - has_conflict  : bool
      - no_data       : bool (True if nothing found)
    """
    # Step 1: Retrieve (permission-aware)
    retrieval = retrieve(query, user_context)
    chunks    = retrieval.get("chunks", [])
    sources   = retrieval.get("sources", [])
    debug     = retrieval.get("debug_info", {})

    no_data      = len(chunks) == 0
    has_conflict = detect_conflict(sources)

    # Step 2: Generate
    answer = generate_answer(
        query        = query,
        chunks       = chunks,
        sources      = sources,
        user_context = user_context,
        has_conflict = has_conflict,
    )

    return {
        "answer":       answer,
        "sources":      sources,
        "debug_info":   debug,
        "chunks_used":  len(chunks),
        "has_conflict": has_conflict,
        "no_data":      no_data,
    }


if __name__ == "__main__":
    # Quick CLI test
    print("=== Appota Internal Wiki — CLI Test ===\n")

    test_cases = [
        {
            "query":   "Tôi được nghỉ bao nhiêu ngày phép mỗi năm?",
            "profile": "Nhân viên Gamota (Nguyễn Văn A)",
        },
        {
            "query":   "Tôi được nghỉ bao nhiêu ngày phép mỗi năm?",
            "profile": "Nhân viên Appota Pay (Trần Thị B)",
        },
        {
            "query":   "Chính sách lương thưởng cấp Manager như thế nào?",
            "profile": "Nhân viên Gamota (Nguyễn Văn A)",
        },
    ]

    for tc in test_cases:
        profile = USER_PROFILES[tc["profile"]]
        print(f"--- [{tc['profile']}] ---")
        print(f"Câu hỏi: {tc['query']}")
        result = run_pipeline(tc["query"], profile)
        print(f"Câu trả lời:\n{result['answer']}")
        print(f"[Debug] chunks={result['chunks_used']} conflict={result['has_conflict']} no_data={result['no_data']}\n")
