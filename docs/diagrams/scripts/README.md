# Mermaid Diagrams for Web Agent Demo

Các biểu đồ Mermaid để trình bày demo hệ thống web agent.

## Danh sách biểu đồ

### 1. System Architecture (system_architecture.mmd)
Kiến trúc tổng thể của hệ thống - các component chính và quan hệ giữa chúng.
- **Sử dụng cho**: Giới thiệu tổng quan hệ thống
- **Thời gian**: Slide đầu tiên của demo

### 2. Agent Workflow (agent_workflow.mmd)
Quy trình xử lý của agent từ khi nhận task đến khi hoàn thành.
- **Sử dụng cho**: Giải thích cách agent hoạt động
- **Thời gian**: Phần demo runtime

### 3. Training Pipeline (training_pipeline.mmd)
Pipeline huấn luyện từ dữ liệu thô đến model.
- **Sử dụng cho**: Giải thích quá trình training
- **Thời gian**: Phần training demo

### 4. Runtime Execution (runtime_execution.mmd)
Luồng thực thi chi tiết của SLMAgent trong production.
- **Sử dụng cho**: Chi tiết hoạt động của agent
- **Thời gian**: Phần technical deep dive

### 5. Data Flow (data_flow.mmd)
Luồng chuyển đổi dữ liệu qua các component.
- **Sử dụng cho**: Giải thích data pipeline
- **Thời gian**: Phần data processing

### 6. Component Interaction (component_interaction.mmd)
Tương tác giữa các component chính (sequence diagram).
- **Sử dụng cho**: Hiểu chi tiết interaction
- **Thời gian**: Q&A session

## Cách sử dụng

### Render trong VS Code
1. Cài extension: Markdown Preview Mermaid Support
2. Mở file .mmd 
3. Preview: Ctrl+Shift+V

### Render online
1. Mở https://mermaid.live/
2. Copy nội dung file .mmd
3. Paste và xem preview

### Export PNG/SVG
1. Dùng mermaid-cli: `mmdc -i diagram.mmd -o diagram.png`
2. Hoặc dùng mermaid.live → Actions → Export

## Thứ tự trình bày đề xuất

1. **system_architecture.mmd** - Bắt đầu với big picture
2. **training_pipeline.mmd** - Giải thích cách train model
3. **agent_workflow.mmd** - Demo cách agent hoạt động
4. **runtime_execution.mmd** - Chi tiết technical
5. **data_flow.mmd** - Luồng dữ liệu
6. **component_interaction.mmd** - Q&A nếu cần

## Tùy chỉnh

Mỗi file .mmd có thể edit trực tiếp để:
- Thay đổi màu sắc
- Thêm/bớt component
- Điều chỉnh text
- Thay đổi layout

Mermaid syntax reference: https://mermaid.js.org/
