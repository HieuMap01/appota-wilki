"""
Streamlit UI for Appota Internal Wiki RAG system.
Run: streamlit run app.py
"""
import sys
import subprocess
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

# ── Auto-ingest on cold start (cloud / Docker / first run) ────────
# If ChromaDB store does not exist or is empty, run ingest automatically.
@st.cache_resource(show_spinner="Khởi tạo cơ sở dữ liệu tri thức...")
def _auto_ingest():
    chroma_dir = Path(__file__).parent / "chromadb_store"
    if not chroma_dir.exists() or not any(chroma_dir.iterdir()):
        subprocess.run(
            [sys.executable, str(Path(__file__).parent / "src" / "ingest.py"), "--reset"],
            check=False,
        )
    return True

_auto_ingest()

from pipeline import run_pipeline, USER_PROFILES

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Appota Internal Wiki",
    page_icon="📚",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header { font-size: 1.8rem; font-weight: 700; color: #1a1a2e; }
    .sub-header  { color: #555; font-size: 0.95rem; margin-top: -8px; }
    .user-badge  {
        background: #e8f5e9; border-left: 4px solid #2d6a4f;
        padding: 10px 14px; border-radius: 4px; margin: 8px 0;
        font-size: 0.9rem;
    }
    .source-box  {
        background: #f0f4f8; border-left: 3px solid #0f3a60;
        padding: 8px 12px; border-radius: 4px; font-size: 0.85rem;
        margin-top: 6px;
    }
    .warn-box {
        background: #fff8e1; border-left: 4px solid #f9a825;
        padding: 10px 14px; border-radius: 4px; margin: 6px 0;
    }
    .no-data-box {
        background: #fce4ec; border-left: 4px solid #c62828;
        padding: 10px 14px; border-radius: 4px;
    }
    div[data-testid="stChatMessage"] { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar: Identity selection ───────────────────────────────────
with st.sidebar:
    st.markdown("## 🏢 Appota Internal Wiki")
    st.markdown("---")

    st.markdown("### 👤 Bạn đang đăng nhập với tư cách:")
    selected_profile_name = st.selectbox(
        label="Chọn danh tính (Mock Identity):",
        options=list(USER_PROFILES.keys()),
        index=0,
    )
    user_ctx = USER_PROFILES[selected_profile_name]

    # Display user badge
    st.markdown(f"""
    <div class="user-badge">
        <b>🏷️ {user_ctx['user_name']}</b><br>
        🏢 Đơn vị: <b>{user_ctx['don_vi'].replace('_', ' ').title()}</b><br>
        📊 Cấp bậc: <b>{user_ctx['cap_bac'].replace('_', ' ').title()}</b>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    show_debug = st.toggle("🔍 Hiển thị Debug Info", value=False)

    st.markdown("---")
    st.markdown("**💡 Câu hỏi gợi ý:**")
    suggestions = [
        "Tôi được nghỉ bao nhiêu ngày phép?",
        "Quy trình onboarding nhân viên mới?",
        "Chính sách bảo mật thông tin?",
        "Tôi được hỗ trợ đào tạo bao nhiêu?",
        "Chính sách lương thưởng Manager?",
        "Quy định làm việc remote?",
    ]
    for s in suggestions:
        if st.button(s, use_container_width=True, key=f"sug_{s}"):
            st.session_state["pending_query"] = s

    st.markdown("---")
    st.caption("⚠️ Dữ liệu giả lập — Appota Internal Wiki MVP")

# ── Main area ─────────────────────────────────────────────────────
st.markdown('<p class="main-header">📚 Appota Internal Wiki</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Tra cứu tri thức nội bộ theo đúng đơn vị và quyền truy cập của bạn.</p>', unsafe_allow_html=True)
st.markdown("---")

# ── Chat history ──────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_profile" not in st.session_state:
    st.session_state.last_profile = selected_profile_name

# Reset chat when user switches identity
if st.session_state.last_profile != selected_profile_name:
    st.session_state.messages = []
    st.session_state.last_profile = selected_profile_name
    st.info(f"Đã chuyển sang danh tính: **{selected_profile_name}**. Lịch sử chat đã được xóa.")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources") and show_debug:
            with st.expander("📎 Nguồn tài liệu & Debug", expanded=False):
                st.json(msg.get("debug_info", {}))

# ── Handle suggestion buttons ─────────────────────────────────────
pending = st.session_state.pop("pending_query", None)

# ── Chat input ────────────────────────────────────────────────────
user_input = st.chat_input("Nhập câu hỏi của bạn...") or pending

if user_input:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Run pipeline
    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm trong hệ thống..."):
            result = run_pipeline(user_input, user_ctx)

        answer     = result["answer"]
        sources    = result["sources"]
        debug      = result["debug_info"]
        no_data    = result["no_data"]
        conflict   = result["has_conflict"]

        # Display answer
        st.markdown(answer)

        # Conflict warning
        if conflict:
            st.markdown("""
            <div class="warn-box">
            ⚠️ <b>Phát hiện nội dung có thể mâu thuẫn giữa các tài liệu.</b>
            Vui lòng xác nhận với HR trước khi áp dụng.
            </div>
            """, unsafe_allow_html=True)

        # No data warning
        if no_data:
            st.markdown("""
            <div class="no-data-box">
            🚫 <b>Không tìm thấy tài liệu phù hợp</b> trong phạm vi quyền truy cập của bạn.
            </div>
            """, unsafe_allow_html=True)

        # Sources
        if sources and not no_data:
            with st.expander("📎 Tài liệu đã sử dụng", expanded=True):
                for s in sources:
                    st.markdown(f"""
                    <div class="source-box">
                    📄 <b>{s.get('doc_id', 'N/A')}</b> &nbsp;|&nbsp;
                    🏢 {s.get('don_vi', 'N/A')} &nbsp;|&nbsp;
                    📅 {s.get('ngay_hieu_luc', 'N/A')} &nbsp;|&nbsp;
                    🎯 Độ khớp: {s.get('similarity', 0):.0%}
                    </div>
                    """, unsafe_allow_html=True)

        # Debug panel
        if show_debug:
            with st.expander("🔍 Debug Info", expanded=False):
                col1, col2, col3 = st.columns(3)
                col1.metric("Chunks retrieved", result["chunks_used"])
                col2.metric("Conflict detected", "Yes" if conflict else "No")
                col3.metric("No data", "Yes" if no_data else "No")
                st.json(debug)

    # Save to history
    st.session_state.messages.append({
        "role":       "assistant",
        "content":    answer,
        "sources":    sources,
        "debug_info": debug,
    })
