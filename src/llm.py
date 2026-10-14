"""
LLM module: Gemini API integration with strict guardrails.
Uses the new google.genai SDK (replaces deprecated google.generativeai).
"""
import sys
from pathlib import Path

from google import genai
from google.genai import types

sys.path.insert(0, str(Path(__file__).parent))
from config import GEMINI_API_KEY, GEMINI_MODEL

# Configure Gemini client (new SDK)
client = genai.Client(api_key=GEMINI_API_KEY)

# Use latest stable flash model (confirmed working)
_MODEL = "gemini-2.5-flash-lite"

# ── System Prompt (guardrails) ────────────────────────────────────
SYSTEM_PROMPT = """Ban la tro ly tri thuc noi bo cua Appota Group.
Nhiem vu cua ban la tra loi cau hoi cua nhan su DUA HOAN TOAN vao cac tai lieu duoc cung cap trong phan CONTEXT.

LUAT BAT BUOC — KHONG DUOC VI PHAM:
1. CHI su dung thong tin co trong CONTEXT. Khong duoc them, suy doan, hoac dung kien thuc ben ngoai.
2. Neu CONTEXT khong du thong tin de tra loi → noi ro: "Toi khong tim thay quy dinh cu the cho truong hop nay trong he thong."
3. Neu co mau thuan giua cac tai lieu ma khong the tu giai quyet → trich dan CA HAI nguon, chi ro diem mau thuan, va yeu cau nhan su xac nhan voi HR. KHONG tu tong hop thanh mot cau tra loi duy nhat.
4. LUON ket thuc cau tra loi bang phan NGUON THAM KHAO liet ke tai lieu da dung.
5. Tra loi bang tieng Viet. Ngan gon, ro rang, dung trong tam.

FORMAT cau tra loi:
[Noi dung tra loi dua tren tai lieu]

📎 **Nguon tham khao:**
- [Ten/ID tai lieu] · [Don vi] · Hieu luc tu [ngay]
"""

CONFLICT_PROMPT_ADDITION = """
CANH BAO: Co nhieu tai lieu lien quan voi noi dung co the khac nhau.
Hay trinh bay ro tung tai lieu noi gi, sau do chi ro diem khac biet.
Khong duoc tu tong hop thanh mot cau tra loi chung.
"""

NO_DATA_RESPONSE = (
    "Tôi không tìm thấy tài liệu nào phù hợp với câu hỏi của bạn "
    "trong phạm vi quyền truy cập của bạn.\n\n"
    "Vui lòng liên hệ HR hoặc quản lý trực tiếp để được hỗ trợ."
)


def build_context(chunks: list[str], sources: list[dict]) -> str:
    """Build the context string from retrieved chunks."""
    if not chunks:
        return ""

    parts = ["=== TAI LIEU THAM KHAO ===\n"]
    seen_families = {}

    for i, (chunk, source) in enumerate(zip(chunks, sources * 10)):
        doc_id = source.get("doc_id", f"doc_{i}")
        if doc_id not in seen_families:
            seen_families[doc_id] = True
            parts.append(
                f"\n--- Tai lieu: {doc_id} | "
                f"Don vi: {source.get('don_vi', 'N/A')} | "
                f"Ngay hieu luc: {source.get('ngay_hieu_luc', 'N/A')} ---"
            )
        parts.append(chunk)

    return "\n".join(parts)


def format_sources(sources: list[dict]) -> str:
    """Format sources for display."""
    if not sources:
        return "Khong co nguon"
    lines = []
    for s in sources:
        lines.append(
            f"- **{s.get('doc_id', 'N/A')}** · "
            f"Don vi: {s.get('don_vi', 'N/A')} · "
            f"Hieu luc: {s.get('ngay_hieu_luc', 'N/A')} · "
            f"Do khop: {s.get('similarity', 0):.0%}"
        )
    return "\n".join(lines)


def generate_answer(
    query: str,
    chunks: list[str],
    sources: list[dict],
    user_context: dict,
    has_conflict: bool = False,
) -> str:
    """
    Generate answer from Gemini with strict guardrails.
    Returns the answer string (already includes source citations).
    """
    if not chunks:
        return NO_DATA_RESPONSE

    context_str = build_context(chunks, sources)
    extra = CONFLICT_PROMPT_ADDITION if has_conflict else ""
    user_info = (
        f"Nguoi hoi: {user_context.get('user_name', 'Nhan su')} | "
        f"Don vi: {user_context.get('don_vi', 'N/A')} | "
        f"Cap bac: {user_context.get('cap_bac', 'N/A')}"
    )

    prompt = f"""{SYSTEM_PROMPT}
{extra}

=== THONG TIN NGUOI HOI ===
{user_info}

{context_str}

=== CAU HOI ===
{query}

=== TRA LOI ==="""

    try:
        response = client.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,   # Low temp for factual Q&A
                max_output_tokens=1024,
            ),
        )
        answer = response.text.strip()

        # Append formatted sources if not already in answer
        if "Nguon tham khao" not in answer and "nguon" not in answer.lower() and sources:
            answer += f"\n\n**Nguon tham khao:**\n{format_sources(sources)}"

        return answer

    except Exception as e:
        return (
            f"Loi khi goi LLM: {str(e)}\n\n"
            f"Debug — Context da retrieve:\n{context_str[:500]}..."
        )


def detect_conflict(sources: list[dict]) -> bool:
    """
    Detect potential conflict: multiple sources from same family,
    same level, but different content/dates.
    """
    if len(sources) < 2:
        return False

    families = {}
    for s in sources:
        fam = s.get("doc_family_id", "")
        unit = s.get("don_vi", "")
        key = (fam, unit)
        if key in families:
            return True
        families[key] = True
    return False
