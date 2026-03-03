# Web Agent System - Tổng Quan

> **🎯 Giải thích ngắn gọn về project này làm gì và làm như thế nào**

---

## 🤔 Project Này Làm Gì?

**Web Agent System** là một hệ thống AI tự động duyệt web như con người:
- 🤖 **AI tự động**: Duyệt web, điền form, click button, nhập text
- 📚 **Thu thập dữ liệu**: Ghi lại mọi thao tác để train AI nhỏ hơn
- 🔍 **Lọc & Kiểm chứng**: LLM validator loại bỏ data không hợp lệ
- 🎓 **Tự học**: AI lớn (LLM) khám phá → tạo tasks → validate → train AI nhỏ (SLM)

**Mục đích**: Tạo một Web Agent nhỏ gọn (SLM) có thể chạy độc lập mà không cần LLM đắt tiền.

**Điểm đặc biệt**:
- ✅ Phase 1 ghi lại MỌI thứ (kể cả actions sai)
- ✅ Phase 3 lọc ra chỉ data chất lượng cao
- ✅ SLM chỉ học từ data đã được kiểm chứng

---

## 🔄 Quy Trình 5 Giai Đoạn

```
Phase 1: Khám Phá Tự Do (Free Exploration)
   ↓ LLM khám phá website một cách tự do
   ↓ Ghi lại MỌI thao tác (có thể đúng hoặc sai)
   ↓ Không lọc, không đánh giá - cứ ghi hết!

Phase 2: Chuẩn Hóa Task (Task Synthesis)
   ↓ LLM đọc các thao tác đã ghi
   ↓ Nhóm các thao tác thành các task có ý nghĩa
   ↓ Output: Danh sách tasks chưa được kiểm chứng

Phase 3: Lọc Task Hợp Lệ (Task Validation)
   ↓ LLM chuyên biệt chạy lại TỪNG task
   ↓ Kiểm tra task nào chạy được, task nào fail
   ↓ ✅ Giữ lại tasks chạy thành công
   ↓ ❌ Loại bỏ tasks không thể chạy được
   ↓ Output: Dữ liệu sạch, đã được kiểm chứng

Phase 4: Huấn Luyện SLM (Training)
   ↓ Dùng dữ liệu sạch từ Phase 3
   ↓ Train một AI nhỏ (Small Language Model)
   ↓ SLM học cách thực hiện tasks như LLM

Phase 5: Đánh Giá (Evaluation)
   ↓ Test SLM trên các website/tasks mới
   ↓ So sánh performance với LLM
```

### 🔍 Chi Tiết Từng Phase

**Phase 1 - Khám Phá:**
- LLM được cung cấp URL và khám phá tự do
- Thử click mọi thứ, điền form, navigate
- **Không care đúng sai** - chỉ ghi lại: screens, actions, transitions
- Example: Click vào button sai → ghi lại; Fill form thiếu data → ghi lại

**Phase 2 - Tổng Hợp:**
- LLM (có thể là model khác) đọc dữ liệu Phase 1
- Nhận diện patterns và tạo tasks có ý nghĩa
- Example: "Click menu → Click product → Add to cart" → Task "Thêm sản phẩm vào giỏ"

**Phase 3 - Validation (QUAN TRỌNG!):**
- LLM **chuyên biệt** (validator agent) nhận tasks từ Phase 2
- Chạy lại TỪNG task trong môi trường thật
- Tasks chạy thành công ✅ → Giữ lại
- Tasks fail ❌ → Ghi log và loại bỏ
- **Đầu ra**: Chỉ có tasks đã được kiểm chứng chạy thành công

**Phase 4 & 5 - Train & Eval:**
- Dùng data sạch để train SLM
- Evaluate trên test set

---

## 🚀 Chạy Thử Ngay

### 1. Cài Đặt
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Cấu Hình API Key
```bash
cp .env.example .env
# Thêm OPENAI_API_KEY hoặc ANTHROPIC_API_KEY vào .env
```

### 3. Chạy Khám Phá
```bash
# Cách 1: Khám phá website bất kỳ
python scripts/run_exploration.py --url https://example.com

# Cách 2: Với LLM synthesis (Phase 2+3)
python scripts/run_exploration.py --url https://example.com --use-llm-synthesis

# Output sẽ được lưu vào:
# - data/raw/example.com/         (dữ liệu khám phá)
# - data/tasks/example.com/       (tasks đã tổng hợp)
```

### 4. Xem Kết Quả
```bash
# Xem danh sách tasks
cat data/tasks/example.com/tasks_summary.txt

# Xem chi tiết JSON
cat data/tasks/example.com/tasks_llm.json
```

---

## 📁 Cấu Trúc Project

```
web-agent/
├── scripts/              # Các script chạy
│   ├── run_exploration.py    # ⭐ Script chính để khám phá
│   └── run_task_synthesis.py # Tổng hợp tasks
├── exploration/          # Logic khám phá & synthesis
│   ├── llm_task_synthesizer.py  # LLM tạo tasks
│   └── task_validator.py        # Kiểm tra tasks
├── agents/               # AI agents
│   ├── simple_agent.py   # Agent đơn giản
│   └── slm_agent.py      # Small Language Model agent
├── training/             # Huấn luyện model
├── browser/              # Điều khiển browser (Playwright)
├── data/                 # Dữ liệu
│   ├── raw/              # Dữ liệu thô từ khám phá
│   └── tasks/            # Tasks đã tổng hợp
├── config/               # Cấu hình
└── docs/                 # Tài liệu
```

---

## 🎯 Ví Dụ Thực Tế

### Input (Command)
```bash
python scripts/run_exploration.py --url https://shop.example.com --use-llm-synthesis
```

### Phase 1: Khám Phá (Exploration)
**LLM Explorer chạy tự do:**
```
✓ Mở https://shop.example.com
✓ Click menu "Products" → Ghi lại
✓ Click "Laptops" category → Ghi lại
✗ Click button sai → Vẫn ghi lại (không quan tâm đúng sai!)
✓ Search box: nhập "gaming laptop" → Ghi lại
✓ Click sản phẩm đầu tiên → Ghi lại
✗ Click "Add to cart" nhưng chưa login → Fail nhưng vẫn ghi lại
✓ Click "Login" → Ghi lại
... (tiếp tục khám phá)
```

**Output Phase 1:**
- `data/raw/shop.example.com/screens.json` (20 screens)
- `data/raw/shop.example.com/actions.json` (45 actions - cả đúng lẫn sai)
- `data/raw/shop.example.com/transitions.json` (60 transitions)

### Phase 2: Tổng Hợp Tasks (Synthesis)
**LLM Synthesizer đọc dữ liệu Phase 1:**
```
LLM phân tích: "Có vẻ user đang cố thêm sản phẩm vào giỏ"
→ Tạo task: "Tìm kiếm và thêm sản phẩm vào giỏ hàng"

LLM nhận diện: "Có sequence login actions"
→ Tạo task: "Đăng nhập vào hệ thống"
```

**Output Phase 2 (Chưa validate):**
```json
{
  "task_id": "T001",
  "description": "Tìm kiếm và thêm sản phẩm vào giỏ hàng",
  "steps": [
    "Click vào ô search",
    "Nhập 'gaming laptop'",
    "Click vào sản phẩm đầu tiên",
    "Click nút 'Add to Cart'"
  ],
  "validated": false
}
```

### Phase 3: Validation (LLM Validator)
**LLM Validator chạy lại TỪNG task:**
```
Testing Task T001: "Tìm kiếm và thêm sản phẩm..."
  Step 1: Click search → ✅ Success
  Step 2: Type "gaming laptop" → ✅ Success
  Step 3: Click first product → ✅ Success
  Step 4: Click "Add to Cart" → ❌ FAIL (Need login first!)

→ Task T001 REJECTED (không chạy được)

---

Testing Task T002: "Đăng nhập vào hệ thống"
  Step 1: Click "Login" → ✅ Success
  Step 2: Enter email → ✅ Success
  Step 3: Enter password → ✅ Success
  Step 4: Click "Submit" → ✅ Success

→ Task T002 ACCEPTED ✅ (chạy thành công!)
```

**Output Phase 3 (Validated - Clean Data):**
```json
{
  "task_id": "T002",
  "description": "Đăng nhập vào hệ thống",
  "steps": [
    "Click 'Login'",
    "Enter email",
    "Enter password",
    "Click 'Submit'"
  ],
  "validated": true,
  "validation_result": "success"
}
```

### Phase 4: Training
```
Input: Chỉ các tasks đã validated (T002, T005, T008...)
Process: Train Small Language Model (SLM)
Output: SLM agent có thể thực hiện tasks tương tự
```

**Kết quả cuối cùng:**
- Có data sạch, đã kiểm chứng
- SLM được train chỉ với data chất lượng cao
- SLM có thể chạy độc lập, không cần LLM đắt tiền

---

## 🔑 Concepts Quan Trọng

### 1. LLM vs SLM
- **LLM** (Large Language Model): AI lớn, thông minh nhưng chậm & đắt (GPT-4, Claude)
- **SLM** (Small Language Model): AI nhỏ, nhanh & rẻ, được train từ dữ liệu LLM tạo ra

### 2. Ba Loại LLM Trong Hệ Thống
- **LLM Explorer** (Phase 1): Khám phá tự do, không cần perfect
- **LLM Synthesizer** (Phase 2): Đọc data và tạo tasks có ý nghĩa
- **LLM Validator** (Phase 3): Chạy lại tasks để lọc ra data sạch
- → Cuối cùng train **SLM** với data đã được validate

### 3. Tại Sao Cần Phase 3 (Validation)?
**Vấn đề:** Phase 1 có thể ghi lại actions sai:
- Click button không tồn tại
- Fill form thiếu required fields
- Navigate đến trang lỗi

**Giải pháp:** Phase 3 lọc bỏ tasks không chạy được:
- LLM Validator = "Quality Control"
- Chỉ tasks chạy thành công mới được dùng để train
- → SLM học từ data chất lượng cao

### 4. Semantic vs Executable
- **Semantic** (Ngữ nghĩa): "Nhấn vào nút đăng nhập" - con người hiểu
- **Executable** (Thực thi): `click(selector="#login-btn")` - máy tính chạy
- ⚠️ **Quy tắc**: KHÔNG BAO GIỜ trộn lẫn 2 loại này!

### 5. URL-Based Storage
- Mỗi website có folder riêng: `data/tasks/example.com/`
- Không bao giờ xóa dữ liệu cũ (trừ khi thủ công)
- Có thể khám phá nhiều website song song

---

## 📚 Tài Liệu Chi Tiết

| File | Mô Tả |
|------|-------|
| [QUICKSTART.md](QUICKSTART.md) | Hướng dẫn setup & sử dụng chi tiết |
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | Trạng thái hiện tại, thay đổi gần đây |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Kiến trúc hệ thống |
| [WORKFLOW.md](WORKFLOW.md) | Quy trình làm việc |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Hướng dẫn đóng góp code |

---

## ❓ Câu Hỏi Thường Gặp

**Q: Tôi cần API key gì?**
A: OpenAI (GPT-4) hoặc Anthropic (Claude) - chọn một trong hai

**Q: Chi phí API bao nhiêu?**
A: ~$0.01-0.10 cho mỗi lần khám phá (tùy website)

**Q: Có thể khám phá localhost không?**
A: Có! `python scripts/run_exploration.py --url http://localhost:9999`

**Q: Dữ liệu được lưu ở đâu?**
A: `data/tasks/{domain}/` - mỗi website một folder riêng

**Q: Tôi mới bắt đầu, làm gì trước?**
A: Đọc [QUICKSTART.md](QUICKSTART.md) và chạy thử với example.com

---

## 🎓 Học Thêm

1. **Setup**: [QUICKSTART.md](QUICKSTART.md)
2. **Hiểu Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
3. **Workflow**: [WORKFLOW.md](WORKFLOW.md)
4. **Đóng góp code**: [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📞 Cần Hỗ Trợ?

- 📖 Đọc [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) để xem trạng thái hiện tại
- 🐛 Check "Known Issues" trong PROJECT_CONTEXT.md
- 📝 Đọc comments trong code
- ✅ Chạy `pytest tests/` để test

---

**🎯 Mục tiêu cuối cùng**: Tạo một Web Agent thông minh, nhỏ gọn, có thể tự động thực hiện các task web phức tạp mà không cần LLM đắt tiền!

_Last Updated: March 4, 2026_
