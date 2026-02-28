### 1. Tổng quan mục tiêu

Xây dựng pipeline explore website theo hướng:

1. LLM đọc màn hình → hiểu context, xác định các hành vi khả thi
2. Agent thực thi từng hành vi → thu thập screen + transition
3. LLM tổng hợp screen + hành vi → sinh danh sách tác vụ
4. Agent thực thi tác vụ → lưu lại trajectory (traj)

Mục tiêu: tự động khám phá cấu trúc UI, thu thập các màn hình, hành vi và chuỗi chuyển trạng thái để phục vụ sinh tác vụ & replay.

---

### 2. Thiết kế hiện tại

- Duyệt theo BFS:
    - Tại mỗi screen: LLM sinh *list action khả thi*.
    - Agent thực thi từng action:
        - Nếu thành công và sang screen mới → lưu screen + transition.
        - Sau đó quay lại screen trước để thực thi các action còn lại.
    - Hết một “tầng screen” → kiểm tra có screen mới không:
        - Nếu không có → dừng explore.
        - Nếu có → tiếp tục sang tầng kế tiếp (dựa trên transition đã lưu để replay đến screen đó).
- Model dùng cho LLM: gpt-4o
- Agent dùng explore: Agenttrek

---

### 3. Tiến độ hoàn thành (đang ở bước 2, 3)

### 3.1 Bước 1: Screen Understanding

- LLM đọc DOM + nội dung hiển thị.
- Sinh danh sách các hành vi có thể thực hiện tại mỗi màn hình.
- Đã có output:

    List<ActionCandidate> cho từng screen.


### 3.2 Bước 2: Action Execution Agent

- Agent nhận:
    - Mô tả hành vi
    - Grounding hint (gợi ý element)
- Thực thi hành vi → ghi nhận:
    - Success/Fail
    - Transition (from_screen → action → to_screen)

### 3.3 Bước 3: Task Synthesis

- LLM tổng hợp toàn bộ screens:
    - mỗi screen sẽ có
        - 1 list action candidate của screen đó
        - 1 list transitions: chứa screen trước đó và action thực thi để chuyển đến screen hiện tại →  để có thể thông tin sinh task tốt hơn
- Sinh danh sách tác vụ khả thi.

### 3.4 Bước 4: Task Execution

- Agent thực thi danh sách tác vụ
- Lưu lại trajectory (traj) để đánh giá và tái sử dụng.

---

### 4. Vấn đề chính hiện tại

### 4.1 Vị trí lỗi trọng tâm: Bước 2 – Grounding

Sau khi LLM sinh action, agent thực thi không thể xác định chính xác element tương ứng với mô tả hành vi.

Hiện tượng:

- Action description: đúng về mặt ngữ nghĩa.
- Nhưng agent không map được mô tả → element cụ thể trong DOM.
- Kết quả:
    - Action fail do click sai element / không tìm thấy element.
    - Tỷ lệ thành công không ổn định.
    - Một số web explore được 7–8 screens.
    - Một số web fail ngay tại trang home.

---

### 4.2 Nguyên nhân phân tích

1. Mô tả hành vi mang tính ngữ nghĩa cao nhưng thiếu định danh cụ thể.
2. DOM thực tế có nhiều element tương tự (button/link giống nhau).
3. Agent đọc lại mô tả → grounding không nhất quán với LLM ban đầu.
4. LLM và agent không chia sẻ cùng “tọa độ tham chiếu” (selector, index, bounding box…).

=> Lỗi cốt lõi: *semantic-action → element grounding mismatch*

---

### 5. Giải pháp đã thử

### 5.1 Thêm Grounding Hint

Với mỗi action:

- Sinh mô tả hành vi (semantic)
- Kèm grounding hint (text label, role, selector gần đúng…)

Ví dụ:

Action: Click "Add to Cart"
Hint: button text contains "Add", role=button, near product title

Kết quả:

- Cải thiện nhẹ khả năng grounding.
- Tuy nhiên vẫn chưa ổn định trên nhiều website.

---

### 6. Kết quả hiện tại

1. Explore chết sớm do fail action tại root screen.
2. Không đo lường chính xác success rate (vì fail do grounding, không phải do action sai).
3. Transition graph thiếu → task synthesis kém chất lượng.
