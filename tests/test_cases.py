"""
Test suite for Appota Internal Wiki RAG system.
Format: Kỳ vọng → Kết quả thực tế → Đạt/Chưa đạt → Điều học được

Run: python tests/test_cases.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pipeline import run_pipeline, USER_PROFILES

# ── ANSI colors for terminal output ──────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

results_log = []

def run_test(tc_id, name, query, user_profile_key, expect_fn, expected_desc, learn_if_fail=""):
    """Run a single test case and log results."""
    print(f"\n{'='*60}")
    print(f"{BOLD}[{tc_id}] {name}{RESET}")
    print(f"Người hỏi : {user_profile_key}")
    print(f"Câu hỏi   : {query}")
    print(f"Kỳ vọng   : {expected_desc}")

    user_ctx = USER_PROFILES[user_profile_key]
    result   = run_pipeline(query, user_ctx)
    passed   = expect_fn(result)
    status   = f"{GREEN}✅ ĐẠT{RESET}" if passed else f"{RED}❌ CHƯA ĐẠT{RESET}"

    print(f"\nKết quả thực tế:")
    print(f"  - no_data     : {result['no_data']}")
    print(f"  - has_conflict: {result['has_conflict']}")
    print(f"  - chunks_used : {result['chunks_used']}")
    sources = result.get("sources", [])
    if sources:
        print(f"  - Tài liệu    : {[s.get('doc_id') for s in sources]}")
    print(f"\nCâu trả lời (100 ký tự đầu):")
    print(f"  {result['answer'][:200]}...")
    print(f"\nKết luận  : {status}")

    log_entry = {
        "id":           tc_id,
        "name":         name,
        "query":        query,
        "user":         user_profile_key,
        "expected":     expected_desc,
        "passed":       passed,
        "no_data":      result["no_data"],
        "has_conflict": result["has_conflict"],
        "chunks_used":  result["chunks_used"],
        "answer_preview": result["answer"][:300],
        "learned":      "" if passed else learn_if_fail,
    }
    results_log.append(log_entry)
    return passed


# ════════════════════════════════════════════════════════════════
# TEST CASES
# ════════════════════════════════════════════════════════════════

def test_all():
    print(f"\n{BOLD}{'='*60}")
    print("  APPOTA INTERNAL WIKI — TEST SUITE")
    print(f"{'='*60}{RESET}")

    # ── TC-01: Core requirement — same question, different users ──
    run_test(
        tc_id   = "TC-01a",
        name    = "Cùng câu hỏi nghỉ phép — Nhân viên Gamota",
        query   = "Tôi được nghỉ bao nhiêu ngày phép mỗi năm?",
        user_profile_key = "Nhân viên Gamota (Nguyễn Văn A)",
        expect_fn   = lambda r: (
            not r["no_data"]
            and any("gamota" in s.get("don_vi","") for s in r["sources"])
            and "15" in r["answer"]  # Gamota has 15 days
        ),
        expected_desc = "Trả về quy định nghỉ phép của Gamota (15 ngày), có nguồn từ Gamota",
        learn_if_fail = "Priority scoring hoặc metadata filter chưa đúng — cần kiểm tra config.py",
    )

    run_test(
        tc_id   = "TC-01b",
        name    = "Cùng câu hỏi nghỉ phép — Nhân viên Appota Pay",
        query   = "Tôi được nghỉ bao nhiêu ngày phép mỗi năm?",
        user_profile_key = "Nhân viên Appota Pay (Trần Thị B)",
        expect_fn   = lambda r: (
            not r["no_data"]
            and any("appota_pay" in s.get("don_vi","") for s in r["sources"])
            and "14" in r["answer"]  # Appota Pay has 14 days
        ),
        expected_desc = "Trả về quy định nghỉ phép của Appota Pay (14 ngày), nguồn từ Appota Pay",
        learn_if_fail = "Hai user khác đơn vị nhưng nhận cùng câu trả lời — filter không hoạt động",
    )

    # ── TC-02: Permission denial — sensitive doc ──────────────────
    run_test(
        tc_id   = "TC-02",
        name    = "Nhân viên truy cập tài liệu mật cấp Manager",
        query   = "Chính sách lương thưởng Manager và Director như thế nào?",
        user_profile_key = "Nhân viên Gamota (Nguyễn Văn A)",
        expect_fn   = lambda r: (
            r["no_data"]
            or "không tìm thấy" in r["answer"].lower()
            or not any("FIN" in s.get("doc_id","") for s in r["sources"])
        ),
        expected_desc = "Từ chối hoặc không trả về nội dung tài liệu DOC-TD-FIN-001 (chỉ dành cho Manager+)",
        learn_if_fail = "NGHIÊM TRỌNG: cap_bac filter không hoạt động — nhân viên đọc được tài liệu mật",
    )

    # ── TC-03: Version conflict — should return newest ────────────
    run_test(
        tc_id   = "TC-03",
        name    = "Hỏi về nghỉ phép Gamota — phải trả về phiên bản 2024",
        query   = "Quy trình xin nghỉ phép tại Gamota như thế nào?",
        user_profile_key = "Nhân viên Gamota (Nguyễn Văn A)",
        expect_fn   = lambda r: (
            not r["no_data"]
            and any("2024" in s.get("ngay_hieu_luc","") for s in r["sources"])
            and not any("OLD" in s.get("doc_id","") for s in r["sources"])
        ),
        expected_desc = "Trả về quy định 2024 (DOC-GMT-HR-001), KHÔNG trả về bản archived 2023",
        learn_if_fail = "Deduplication tại ingest time chưa hoạt động — bản archived vẫn được retrieve",
    )

    # ── TC-04: No data in system ──────────────────────────────────
    run_test(
        tc_id   = "TC-04",
        name    = "Câu hỏi không có dữ liệu trong hệ thống",
        query   = "Quy định sử dụng phòng gym tại văn phòng như thế nào?",
        user_profile_key = "Nhân viên Gamota (Nguyễn Văn A)",
        expect_fn   = lambda r: (
            r["no_data"]
            or "không tìm thấy" in r["answer"].lower()
            or r["chunks_used"] == 0
        ),
        expected_desc = "Fallback rõ ràng — không bịa, nói không có thông tin",
        learn_if_fail = "LLM đang hallucinate thông tin không có trong tài liệu — cần thắt chặt system prompt",
    )

    # ── TC-05: Priority — unit-specific beats group-level ─────────
    run_test(
        tc_id   = "TC-05",
        name    = "Onboarding Gamota phải ưu tiên quy trình của Gamota",
        query   = "Quy trình onboarding nhân viên mới tại đây như thế nào?",
        user_profile_key = "Nhân viên Gamota (Nguyễn Văn A)",
        expect_fn   = lambda r: (
            not r["no_data"]
            and any("gamota" in s.get("don_vi","") for s in r["sources"])
            # Gamota onboarding should be preferred over Tap Doan general
        ),
        expected_desc = "Ưu tiên quy trình onboarding của Gamota (DOC-GMT-HR-002) hơn quy trình chung Tập đoàn",
        learn_if_fail = "Priority scoring chưa đúng — quy trình Tập đoàn được ưu tiên thay vì quy trình công ty con",
    )

    # ── TC-06: Hard case — ambiguous question ─────────────────────
    run_test(
        tc_id   = "TC-06",
        name    = "[KHÓ] Câu hỏi mơ hồ — không rõ áp dụng cho loại tài liệu nào",
        query   = "Tôi cần biết về các quy định",
        user_profile_key = "Nhân viên Appota Pay (Trần Thị B)",
        expect_fn   = lambda r: True,  # Any response is acceptable, we observe behavior
        expected_desc = "Hệ thống cần hỏi clarification hoặc liệt kê các chủ đề có sẵn — [Quan sát hành vi]",
        learn_if_fail = "Câu hỏi quá chung chung — hệ thống cần hỏi thêm hoặc trả về danh sách chủ đề",
    )

    # ── TC-07: Known failure case ─────────────────────────────────
    run_test(
        tc_id   = "TC-07",
        name    = "[THẤT BẠI DỰ KIẾN] Manager Gamota hỏi tài liệu mật Tập đoàn",
        query   = "Cơ cấu lương thưởng Director cụ thể là bao nhiêu?",
        user_profile_key = "Team Lead Gamota (Lê Văn C)",
        expect_fn   = lambda r: (
            # Critical: DOC-TD-FIN-001 (salary doc) must NOT appear in sources
            not any("FIN" in s.get("doc_id","") for s in r["sources"])
        ),
        expected_desc = "[Dự kiến thất bại một phần] Team Lead KHÔNG thấy DOC-TD-FIN-001 (Manager-only) — nhưng hệ thống có thể vẫn trả về chunk không liên quan khác",
        learn_if_fail = "Cross-unit + cross-level permission cần được test kỹ hơn trong production",
    )

    # ── SUMMARY ───────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"{BOLD}KẾT QUẢ TỔNG HỢP{RESET}")
    print(f"{'='*60}")

    passed_count = sum(1 for r in results_log if r["passed"])
    total        = len(results_log)

    for r in results_log:
        icon = "✅" if r["passed"] else "❌"
        print(f"  {icon} [{r['id']}] {r['name']}")
        if not r["passed"] and r["learned"]:
            print(f"       → Điều học được: {r['learned']}")

    print(f"\n{'='*60}")
    print(f"Kết quả: {passed_count}/{total} test cases passed")

    if passed_count == total:
        print(f"{GREEN}Tất cả test cases đạt!{RESET}")
    elif passed_count >= total * 0.7:
        print(f"{YELLOW}Một số test cases chưa đạt — cần review.{RESET}")
    else:
        print(f"{RED}Nhiều test cases thất bại — cần debug.{RESET}")

    return results_log


if __name__ == "__main__":
    test_all()
