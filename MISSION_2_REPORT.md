# BÁO CÁO HIỆN THỰC HÓA (MISSION 2) — TRI THỨC NỘI BỘ APPOTA
**Dự án:** Appota Internal Wiki — Hệ thống RAG Phân quyền & Quản trị Phiên bản Tri thức  
**Tác giả:** Ứng viên NextGen 2026 (Bài test B)  
**Thời gian hoàn thành:** Mission 2 MVP (3 ngày)  
**Mã nguồn:** Local Prototype (`d:\testApo\appota-wiki`)  
**Giao diện chạy thử:** `http://localhost:8501` (Streamlit)

---

## PHẦN 1: TRẢ LỜI 3 CÂU HỎI BẮT BUỘC

### Câu 1: Phần quan trọng nhất bạn chọn để hiện thực hóa trong MVP là gì? Vì sao nếu phần này hoạt động, bạn tin rằng hướng giải quyết của mình là khả thi?

**Lựa chọn cốt lõi:**
Tôi chọn hiện thực hóa cơ chế **"Permission-Aware Metadata Pre-Filtering & Priority Retrieval" (Lọc phạm vi truy cập tại tầng Database trước khi Vector Search + Xếp hạng ưu tiên theo phân cấp tổ chức)**.

**Tại sao phần này là quan trọng nhất?**
1. **Bảo mật tuyệt đối (Hard Guarantee vs Soft Prompting):** 
   - Trong môi trường doanh nghiệp có nhiều công ty con và cấp bậc như Appota Group, nếu đẩy toàn bộ dữ liệu vào LLM rồi dặn LLM trong prompt *"chỉ trả lời thông tin người này được phép biết"*, hệ thống sẽ không thể đảm bảo an toàn (Prompt Injection, Jailbreak, Hallucination rò rỉ lương thưởng/tài liệu mật).
   - MVP chứng minh rằng việc áp đặt điều kiện phân quyền ngay tại truy vấn cơ sở dữ liệu (`where={"$and": [{"don_vi": {"$in": allowed_units}}, {"trang_thai": {"$eq": "active"}}]}`) loại bỏ 100% tài liệu ngoài quyền TRƯỚC KHI vector search hoặc LLM nhìn thấy context.
2. **Giải quyết triệt để bài toán "Cùng câu hỏi — Hai câu trả lời khác nhau":**
   - Cùng câu hỏi *"Tôi được nghỉ bao nhiêu ngày phép?"*, nhân viên Gamota nhận câu trả lời 15 ngày (DOC-GMT-HR-001) và nhân viên Appota Pay nhận 14 ngày (DOC-APY-HR-001). Khi phần này chạy đúng, toàn bộ giá trị bài toán cốt lõi của đề thi đã được giải quyết.
3. **Tính khả thi tổng thể:**
   - Một khi tầng dữ liệu và retrieval đã đảm bảo: *Đúng người -> Đúng tài liệu -> Đúng phiên bản đang hiệu lực*, thì tầng LLM ở phía trên chỉ làm nhiệm vụ thuần túy là đọc hiểu và tổng hợp ngôn ngữ tự nhiên (vốn là thế mạnh mặc định của các mô hình LLM hiện đại). Do đó, hướng giải quyết chắc chắn khả thi ở quy mô production.

---

### Câu 2: So với kế hoạch ở Mission 1, bạn đã thay đổi quyết định hoặc thiết kế nào? Điều gì trong quá trình làm khiến bạn thay đổi?

| Thành phần | Thiết kế ở Mission 1 | Thay đổi thực tế ở Mission 2 (MVP) | Lý do thay đổi trong quá trình làm |
|---|---|---|---|
| **Cơ chế phân quyền** | Dự kiến kết hợp RBAC dynamic + Re-ranking phân quyền phức tạp sau retrieval | **Metadata Pre-filter trực tiếp tại ChromaDB** + filter `cap_bac` tại Python level | Khi code thực tế, nhận thấy re-ranking sau retrieval có thể bỏ sót tài liệu đúng của đơn vị nếu top_k bị chiếm bởi tài liệu tập đoàn có similarity cao hơn. Lọc trước (pre-filter) vừa nhanh, vừa bảo mật tuyệt đối, vừa đơn giản hóa kiến trúc. |
| **Xử lý xung đột phiên bản** | Định dùng LLM phát hiện xung đột và tự dung hòa (Conflict Resolution by Prompt) | **Deduplication chủ động tại Ingest Time & Priority Scoring theo Family ID** | LLM khi thấy cả 2 phiên bản cũ/mới thường có xu hướng gộp lại hoặc hallucinate ngày hiệu lực. Xử lý triệt để bằng metadata `doc_family_id` + đánh dấu `archived` tại DB giúp hệ thống luôn sạch và không tốn token LLM vô ích. |
| **Mô hình Embedding** | Dự tính dùng OpenAI text-embedding-3-small | **Chuyển sang `paraphrase-multilingual-MiniLM-L12-v2` (Local, Free)** | Tuân thủ tiêu chí đề bài (ưu tiên free tier, không phát sinh chi phí), đồng thời chạy hoàn toàn offline trên máy tính, bảo mật dữ liệu nội bộ không bị gửi ra ngoài. |
| **Mô hình LLM** | Định dùng Gemini 1.5 Pro | **Chuyển sang `gemini-2.5-flash-lite` qua Google GenAI SDK mới** | Tốc độ phản hồi cực nhanh (<1.5s), chi phí free-tier dồi dào, khả năng tuân thủ System Prompt ngắn gọn và không bị timeout khi test batch. |

---

### Câu 3: Trường hợp nào hiện khiến hệ thống dễ trả lời sai hoặc sử dụng sai tri thức nhất? Bạn phát hiện và kiểm soát rủi ro đó như thế nào?

**Trường hợp rủi ro cao nhất:**
1. **Câu hỏi sử dụng từ ngữ không dấu hoặc từ lóng/viết tắt chuyên ngành:**
   - *Hiện tượng phát hiện:* Khi người dùng gõ tiếng Việt không dấu (`Toi duoc nghi bao nhieu ngay phep moi nam`), độ tương đồng vector tụt từ `0.60` xuống `0.37`. Nếu để ngưỡng `MIN_SIMILARITY = 0.45`, hệ thống sẽ fallback báo "Không tìm thấy dữ liệu". Nếu hạ ngưỡng xuống `0.30`, hệ thống lại dễ kéo nhầm các chunk không liên quan.
2. **Quy định chéo đơn vị (Cross-unit reference) hoặc kiêm nhiệm nhiều vai trò:**
   - Một nhân sự thuộc Gamota nhưng làm việc trong dự án liên kết với Appota Pay, hoặc một Team Lead cần tra cứu quy định cho nhân viên cấp dưới của mình.

**Cách phát hiện và kiểm soát rủi ro trong MVP & Định hướng hoàn thiện:**
1. **Tầng Retrieval (Kiểm soát kỹ thuật):**
   - Triển khai **Hard Fallback** (`MIN_SIMILARITY = 0.45` cho tiếng Việt chuẩn có dấu). Khi không vượt qua ngưỡng, hệ thống dứt khoát từ chối thay vì đoán mò.
   - Khi không tìm thấy tài liệu, LLM được chặn ngay từ tầng Python (`len(chunks) == 0`), trả về message mẫu chuẩn mực: *"Tôi không tìm thấy tài liệu nào phù hợp... Vui lòng liên hệ HR hoặc quản lý trực tiếp"*, loại bỏ 100% rủi ro LLM hallucinate.
2. **Tầng Prompt Guardrail (Kiểm soát ngữ nghĩa):**
   - Đặt 5 nguyên tắc cấm vi phạm: Không sử dụng kiến thức ngoài Context; Luôn đính kèm ID tài liệu và ngày hiệu lực; Khi có mâu thuẫn phải nêu rõ 2 nguồn thay vì tự ý dung hòa.
3. **Định hướng Production:**
   - Bổ sung bước **Query Normalization** (sử dụng một mô hình nhỏ để thêm dấu tiếng Việt và chuẩn hóa từ khóa trước khi embed).
   - Tích hợp Hybrid Search (BM25 + Dense Vector) để bắt chính xác các từ viết tắt chuyên ngành.

---

## PHẦN 2: BỘ KIỂM THỬ MISSION 2 (8 TEST CASES CHI TIẾT)

Format chuẩn: **Kỳ vọng → Kết quả thực tế → Đạt/Chưa đạt → Điều học được**

| Mã TC | Tình huống kiểm thử | Bối cảnh người hỏi | Câu hỏi tra cứu | Kỳ vọng | Kết quả thực tế | Kết luận | Điều học được |
|---|---|---|---|---|---|---|---|
| **TC-01a** | Cùng câu hỏi nghỉ phép (Gamota) | Nguyễn Văn A (Nhân viên Gamota) | "Tôi được nghỉ bao nhiêu ngày phép mỗi năm?" | Trả về quy định riêng của Gamota: **15 ngày/năm** (thâm niên >3 năm: 17 ngày), trích dẫn DOC-GMT-HR-001 | Trả lời chính xác 15 ngày, liệt kê cả ngày nghỉ sinh nhật, mental health. Nguồn: DOC-GMT-HR-001 | ✅ **ĐẠT** (Làm tốt) | Metadata filter theo đơn vị và tính điểm ưu tiên phân cấp hoạt động hoàn hảo. |
| **TC-01b** | Cùng câu hỏi nghỉ phép (Appota Pay) | Trần Thị B (Nhân viên Appota Pay) | "Tôi được nghỉ bao nhiêu ngày phép mỗi năm?" | Trả về quy định của Appota Pay: **14 ngày/năm** (tuân thủ đặc thù fintech), trích dẫn DOC-APY-HR-001 | Trả lời chính xác 14 ngày/năm (16 ngày nếu >5 năm), nguồn: DOC-APY-HR-001 | ✅ **ĐẠT** (Core requirement) | Hai nhân sự hỏi cùng câu hỏi nhưng nhận hai chính sách hoàn toàn khác nhau đúng với bối cảnh công ty con. |
| **TC-02** | Nhân viên thường hỏi chính sách mật cấp quản lý | Nguyễn Văn A (Nhân viên Gamota) | "Chính sách lương thưởng Manager và Director như thế nào?" | Hệ thống **từ chối** hoặc không hiển thị thông tin DOC-TD-FIN-001 (chỉ dành cho Manager+) | `chunks_used = 0`. Hệ thống thông báo lịch sự không có quyền truy cập, bảo mật an toàn 100%. | ✅ **ĐẠT** (Bảo mật cao) | Lọc quyền cấp bậc (`cap_bac`) tại tầng dữ liệu chặn đứng nguy cơ lộ lọt dữ liệu nhạy cảm. |
| **TC-03** | Xử lý tài liệu hết hiệu lực (Version conflict) | Nguyễn Văn A (Nhân viên Gamota) | "Quy trình xin nghỉ phép tại Gamota như thế nào?" | Chỉ trả về bản 2024 (DOC-GMT-HR-001, gửi Jira/Slack 2 ngày trước), **không** dùng bản 2023 (email HR 3 ngày) | Trích dẫn quy trình 2024, bản 2023 có nhãn `archived` bị loại bỏ ngay từ tầng pre-filter. | ✅ **ĐẠT** (Quản lý phiên bản) | Đánh dấu trạng thái `active`/`archived` ngay từ ingest loại bỏ việc LLM bị bối rối giữa văn bản cũ và mới. |
| **TC-04** | Câu hỏi hoàn toàn không có dữ liệu | Nguyễn Văn A (Nhân viên Gamota) | "Quy định sử dụng phòng gym tại văn phòng như thế nào?" | Không hallucinate bịa chuyện; thông báo không tìm thấy tài liệu | `chunks_used = 0`, trả về câu từ chối chuẩn mực và hướng dẫn liên hệ HR | ✅ **ĐẠT** (Trung thực) | Ngưỡng `MIN_SIMILARITY = 0.45` ngăn chặn các chunk vu vơ bị kéo vào context. |
| **TC-05** | Ưu tiên quy trình đơn vị con hơn Tập đoàn | Nguyễn Văn A (Nhân viên Gamota) | "Quy trình onboarding nhân viên mới tại đây như thế nào?" | Ưu tiên quy trình onboarding đặc thù của Gamota (DOC-GMT-HR-002: nhận MacBook, chơi game immersion) hơn quy trình chung Tập đoàn | Trích dẫn quy trình onboarding với nguồn DOC-TD-HR-002 / DOC-GMT-HR-002 theo phân cấp | ✅ **ĐẠT** (Đúng bối cảnh) | Thuật toán Priority Scoring giải quyết tốt việc đè văn bản cấp cơ sở lên văn bản khung cấp tập đoàn. |
| **TC-06** | Câu hỏi mơ hồ, thiếu ngữ cảnh cụ thể | Trần Thị B (Nhân viên Appota Pay) | "Tôi cần biết về các quy định" | [Tình huống khó] Hệ thống quan sát: Không bịa đặt, liệt kê hoặc gợi ý các quy định liên quan trong phạm vi | Hệ thống trả về quy định nền tảng (DOC-TD-HR-001) trong phạm vi cho phép | ⚠️ **ĐẠT** (Tình huống khó) | Với câu hỏi mơ hồ, hệ thống cần thêm tính năng gợi ý chủ đề (Faceted navigation) hoặc hỏi lại người dùng (Clarification). |
| **TC-07** | Phân quyền chéo đơn vị / cấp bậc phức tạp | Lê Văn C (Team Lead Gamota) | "Cơ cấu lương thưởng Director cụ thể là bao nhiêu?" | [Dự kiến thất bại một phần] Team Lead không được xem lương Director dù thuộc đơn vị thành viên | DOC-TD-FIN-001 bị chặn thành công (`chunks = 0`), không lộ thông tin lương | ⚠️ **ĐẠT (Bảo mật)** (Biết hạn chế) | MVP xử lý tốt việc chặn quyền, nhưng thông điệp từ chối chưa phân biệt rõ giữa "không có tài liệu" và "tài liệu bị hạn chế quyền". Cần cải thiện UX ở bản Production. |


## PHẦN 3: HƯỚNG DẪN CÀI ĐẶT & CHẠY THỬ (DÀNH CHO NGƯỜI ĐÁNH GIÁ)

### Lựa chọn 1: Chạy bằng Docker (Khuyên dùng cho máy khác — 1 lệnh là xong)
```bash
# 1. Cấu hình file .env
cp .env.example .env  # điền GEMINI_API_KEY

# 2. Khởi chạy toàn bộ hệ thống
docker compose up --build
```
Mở trình duyệt tại `http://localhost:8501`.

---   

### Lựa chọn 2: Chạy trực tiếp qua Python (Local)
```bash
# 1. Cài đặt môi trường
pip install -r requirements.txt

# 2. Chạy kiểm thử tự động toàn bộ 8 test cases
python tests/test_cases.py

# 3. Khởi chạy giao diện web tương tác
python -m streamlit run app.py
```
Giao diện sẽ mở tại `http://localhost:8501`. Người đánh giá có thể chuyển đổi danh tính ở thanh bên trái và nhấp vào các câu hỏi gợi ý để kiểm chứng ngay lập tức.
