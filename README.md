# Appota Internal Wiki
**AI-Powered Permission-Aware Knowledge System**

> Mission 2 — NextGen 2026 | Bài test B

---

## Bài toán
Appota Group vận hành cấu trúc tổ chức 4 cấp (Tập đoàn → Công ty → Phòng ban → Nhóm). Nhân sự cần tra cứu tri thức nội bộ nhưng:
- Không biết quy định nào áp dụng cho đơn vị mình
- Dễ đọc nhầm quy định của đơn vị khác
- Có thể vô tình truy cập thông tin ngoài phạm vi cho phép

**Core Loop:** Câu hỏi + bối cảnh người dùng → Tìm đúng tri thức (đúng phạm vi) → Trả lời có nguồn kiểm chứng.

---

## Kiến trúc giải pháp

```
User Query + Identity Context
    ↓
[STEP 1] Metadata Pre-Filter (ChromaDB WHERE clause)
         → Loại NGAY tài liệu ngoài phạm vi TRƯỚC khi vector search
    ↓
[STEP 2] Vector Similarity Search (cosine distance)
         → Tìm tài liệu liên quan trong tập đã lọc
    ↓
[STEP 3] Priority Scoring (Python code)
         → Phòng ban (3) > Công ty (2) > Tập đoàn (1)
    ↓
[STEP 4] Conflict Detection + LLM Guardrail
         → Gemini Flash với system prompt cứng
    ↓
Câu trả lời có nguồn trích dẫn
```

**Tech Stack:**
- Embedding: `paraphrase-multilingual-MiniLM-L12-v2` (local, free)
- Vector DB: ChromaDB (local persistent)
- LLM: Google Gemini 1.5 Flash (free tier)
- UI: Streamlit

---

## Cài đặt & Khởi chạy

### Cách 1: Chạy bằng Docker (Khuyên dùng cho máy khác / Giám khảo test)
Chỉ cần cài đặt Docker Desktop, mở terminal tại thư mục dự án và chạy:
```bash
# 1. Tạo file .env và điền GEMINI_API_KEY
cp .env.example .env

# 2. Khởi chạy toàn bộ hệ thống (tự động build, ingest dữ liệu và mở app)
docker compose up --build
```
Mở trình duyệt truy cập: **http://localhost:8501**

---

### Cách 2: Chạy trực tiếp bằng Python (Local)

1. **Clone repo & tạo môi trường:**
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

2. **Cài dependencies:**
```bash
pip install -r requirements.txt
```

3. **Cấu hình API Key:**
```bash
cp .env.example .env
# Mở file .env và điền GEMINI_API_KEY
```

4. **Ingest dữ liệu & Khởi chạy:**
```bash
python src/ingest.py --reset
python -m streamlit run app.py
```
Mở trình duyệt tại: **http://localhost:8501**

---

## Báo cáo nộp bài Mission 2
> 📄 Xem toàn văn báo cáo trả lời 3 câu hỏi bắt buộc & kịch bản video 5 phút tại: [MISSION_2_REPORT.md](file:///d:/VinUni/testApo/appota-wiki/MISSION_2_REPORT.md)

---

## Chạy Test Cases

```bash
python tests/test_cases.py
```

**Bộ test gồm 8 test cases (Kết quả thực tế: 8/8 PASSED):**
| ID | Tình huống kiểm thử | Bối cảnh người hỏi | Kết quả | Trạng thái |
|---|---|---|---|---|
| **TC-01a** | Cùng câu hỏi nghỉ phép → Nhận quy định Gamota (15 ngày) | NV Gamota | Đạt: đúng 15 ngày, nguồn Gamota | ✅ Làm tốt |
| **TC-01b** | Cùng câu hỏi nghỉ phép → Nhận quy định Appota Pay (14 ngày) | NV Appota Pay | Đạt: đúng 14 ngày, nguồn Appota Pay | ✅ Core requirement |
| **TC-02** | Nhân viên thường truy cập tài liệu mật cấp Manager | NV Gamota | Đạt: từ chối truy cập, bảo mật 100% | ✅ Bảo mật cao |
| **TC-03** | Phiên bản 2024 được ưu tiên hơn 2023 (archived) | NV Gamota | Đạt: chỉ dùng bản 2024, bỏ bản cũ | ✅ Quản lý phiên bản |
| **TC-04** | Câu hỏi không có dữ liệu (phòng gym) → fallback rõ ràng | NV Gamota | Đạt: không bịa, thông báo trung thực | ✅ Không hallucinate |
| **TC-05** | Onboarding Gamota ưu tiên hơn quy trình chung Tập đoàn | NV Gamota | Đạt: ưu tiên quy trình cơ sở | ✅ Đúng bối cảnh |
| **TC-06** | Câu hỏi mơ hồ ("Tôi cần biết về các quy định") | NV Appota Pay | Đạt: trả về quy định nền tảng | ⚠️ Tình huống khó |
| **TC-07** | Phân quyền chéo (Team Lead hỏi lương Director) | TL Gamota | Đạt: DOC-TD-FIN-001 bị chặn an toàn | ⚠️ Biết hạn chế |

---

## Hạn chế đã biết của MVP
- **Mock identity:** Người dùng tự chọn danh tính qua dropdown, không có xác thực thật (SSO/JWT).
- **Dữ liệu giả lập:** ~10 tài liệu, không phản ánh độ phức tạp của hệ thống thực.
- **Single-turn:** Không có memory hội thoại đa lượt.
- **Tiếng Việt:** Embedding model chưa tối ưu hoàn toàn cho tiếng Việt có dấu phức tạp.
- **TC-07:** Cross-unit + cross-level permission chưa xử lý hoàn toàn.

---

## Nhật ký Bằng chứng (AI Tools Used)

| Công cụ | Mục đích | Xác minh |
|---|---|---|
| Antigravity (Claude/Gemini) | Phân tích đề bài, thiết kế kiến trúc, viết code | Review từng file, test thủ công, sửa bug |
| GPT-4o (qua Antigravity) | Generate 10 tài liệu giả lập theo schema | Đọc lại từng file, verify metadata YAML |

**Quyết định độc lập:** Chọn xử lý permission bằng Metadata filter tại tầng DB (không để LLM phán xét) — quyết định này dựa trên hiểu biết về rủi ro hallucination của LLM trong tác vụ cần tính nhất quán tuyệt đối.
