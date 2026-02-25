# Phase 3: Task Synthesis Workflow

Hướng dẫn thực hiện Phase 3 (Task Synthesis) sau khi đã có kết quả từ Phase 2 (Exploration).

## 🎯 Tự động chạy (Khuyến nghị)

**Task synthesis sẽ tự động chạy sau exploration!**

Khi bạn chạy exploration, Phase 3 sẽ tự động được thực hiện:

```bash
# Phase 2 + Phase 3 tự động
python run_exploration.py --url http://localhost:9999

# Kết quả:
# - Phase 2: data/raw/agenttrek/  (screens, actions, transitions, metadata)
# - Phase 3: data/tasks/agenttrek/ (tasks.json, tasks_summary.txt)
```

Để bỏ qua task synthesis tự động:

```bash
python run_exploration.py --url http://localhost:9999 --skip-task-synthesis
```

## Tổng quan

**Input**: 4 files từ exploration
- `screens.jsonl` - Thông tin các màn hình đã khám phá (JSONL format)
- `actions.jsonl` - Thông tin các actions (JSONL format)
- `transitions.jsonl` - Thông tin các transitions (JSONL format)
- `metadata.json` - Metadata về quá trình exploration (JSON format)

**Lưu ý**: Các file `.jsonl` là JSON Lines format - mỗi dòng là một JSON object riêng biệt.

**Output**: Task graph
- `tasks.json` - Các user tasks đã được tổng hợp
- `tasks_summary.txt` - Bản tóm tắt dễ đọc

---

## Cách 1: Chạy thủ công (Manual) - Khi cần chạy lại

Nếu bạn đã có dữ liệu exploration sẵn và muốn chạy lại task synthesis:

### Cài đặt

Không cần cài thêm gì, đã có sẵn trong project.

### Chạy với auto-detection (tự động nhận diện domain)

```bash
python scripts/run_task_synthesis.py \
    --input data/raw/agenttrek \
    --output data/tasks/agenttrek
```

### Chạy với domain cụ thể

```bash
# E-commerce
python scripts/run_task_synthesis.py \
    --input data/raw/agenttrek \
    --output data/tasks/agenttrek \
    --domain ecommerce

# News site
python scripts/run_task_synthesis.py \
    --input data/raw/news_site \
    --output data/tasks/news_site \
    --domain news

# Social media
python scripts/run_task_synthesis.py \
    --input data/raw/social_site \
    --output data/tasks/social_site \
    --domain social
```

### Options

- `--input`, `-i`: Thư mục chứa kết quả exploration (bắt buộc)
- `--output`, `-o`: Thư mục lưu kết quả task synthesis (bắt buộc)
- `--domain`, `-d`: Domain type (`ecommerce`, `news`, `social`, `banking`, `streaming`, `generic`)
- `--verbose`, `-v`: Hiển thị log chi tiết

### Ví dụ đầy đủ

```bash
# Chạy với verbose logging
python scripts/run_task_synthesis.py \
    --input data/raw/agenttrek \
    --output data/tasks/agenttrek \
    --domain ecommerce \
    --verbose
```

## Cách 2: Sử dụng Python API

### Code mẫu

```python
import json
from pathlib import Path
from exploration import TaskSynthesizer, Screen, ActionSemantic, ScreenType

# 1. Load screens từ file
input_dir = Path("data/raw/agenttrek")
with open(input_dir / "screens.json", 'r') as f:
    screens_data = json.load(f)

# 2. Convert sang Screen objects
screens = []
for screen_data in screens_data:
    screen = Screen(
        screen_id=screen_data['screen_id'],
        url=screen_data['url'],
        dom_snapshot=screen_data.get('dom_snapshot', ''),
        visible_text=screen_data.get('visible_text', ''),
        semantic_summary=screen_data.get('semantic_summary', ''),
        screen_type=ScreenType(screen_data['screen_type']),
        timestamp=screen_data['timestamp']
    )
    
    # Add actions
    screen.actions = [
        ActionSemantic.from_dict(a) 
        for a in screen_data.get('actions', [])
    ]
    
    screens.append(screen)

# 3. Chạy task synthesis
synthesizer = TaskSynthesizer()  # Auto-detect domain
# hoặc: synthesizer = TaskSynthesizer(domain="ecommerce")

task_graph = synthesizer.synthesize(screens)

# 4. Lưu kết quả
output_dir = Path("data/tasks/agenttrek")
output_dir.mkdir(parents=True, exist_ok=True)

with open(output_dir / "tasks.json", 'w') as f:
    json.dump(task_graph.to_dict(), f, indent=2)

print(f"Generated {len(task_graph.tasks)} tasks")
```

## Cách 3: Workflow hoàn chỉnh

### Script tích hợp Phase 2 → Phase 3

```python
from pathlib import Path
from exploration import run_exploration, TaskSynthesizer

# Phase 2: Exploration
print("Phase 2: Running exploration...")
exploration_result = run_exploration(
    start_url="https://example.com",
    explorer="agenttrek"
)

# Lưu exploration results
output_dir = Path("data/raw/example_site")
# ... save exploration results ...

# Phase 3: Task Synthesis
print("Phase 3: Synthesizing tasks...")
screens = list(exploration_result.screens.values())
synthesizer = TaskSynthesizer()
task_graph = synthesizer.synthesize(screens)

# Lưu tasks
tasks_dir = Path("data/tasks/example_site")
tasks_dir.mkdir(parents=True, exist_ok=True)

import json
with open(tasks_dir / "tasks.json", 'w') as f:
    json.dump(task_graph.to_dict(), f, indent=2)

print(f"✓ Complete! Generated {len(task_graph.tasks)} tasks")
```

## Cấu trúc thư mục

### Input (Exploration Results)

```
data/raw/agenttrek/
├── screens.json          # Bắt buộc
├── actions.json          # Optional
├── transitions.json      # Optional
└── metadata.json         # Optional
```

### Output (Task Synthesis)

```
data/tasks/agenttrek/
├── tasks.json           # Complete task graph (JSON)
└── tasks_summary.txt    # Human-readable summary
```

## Format files

### Input: screens.json

```json
[
  {
    "screen_id": "screen_001",
    "url": "https://example.com",
    "screen_type": "homepage",
    "semantic_summary": "Homepage with search functionality",
    "visible_text": "Welcome to...",
    "timestamp": "2026-02-24T10:00:00",
    "actions": [
      {
        "action_id": "a_001",
        "intent": "search",
        "object": "products",
        "context": "via search input",
        "description": "Search for products",
        "confidence": 0.9
      }
    ]
  }
]
```

### Output: tasks.json

```json
{
  "tasks": [
    {
      "task_id": "task_abc123",
      "name": "search products",
      "description": "Search and filter products",
      "related_actions": ["a_001", "a_002"],
      "confidence": 0.95,
      "entry_screens": ["screen_001", "screen_002"],
      "priority": "initial",
      "meta": {
        "action_count": 2,
        "screen_count": 2
      }
    }
  ],
  "meta": {
    "total_screens": 5,
    "total_actions": 11,
    "unique_actions": 9
  }
}
```

### Output: tasks_summary.txt

```
================================================================================
TASK SYNTHESIS SUMMARY
================================================================================

Total tasks: 7
Total screens: 5
Total actions: 11
Unique actions: 9

INITIAL TASKS (2):
--------------------------------------------------------------------------------

  Task: search products
  ID: task_abc123
  Description: Search and filter products
  Confidence: 0.95
  Related Actions: 2
  Entry Screens: 2
...
```

## Xử lý lỗi thường gặp

### Error: "screens.json not found"

**Nguyên nhân**: Không tìm thấy file screens.json

**Giải pháp**:
```bash
# Kiểm tra file có tồn tại
ls data/raw/agenttrek/

# Đảm bảo đường dẫn đúng
python scripts/run_task_synthesis.py --input data/raw/agenttrek --output data/tasks
```

### Error: "No screens found"

**Nguyên nhân**: File screens.json rỗng hoặc không có semantic actions

**Giải pháp**:
```python
# Kiểm tra nội dung file
import json
with open("data/raw/agenttrek/screens.json") as f:
    data = json.load(f)
    print(f"Found {len(data)} screens")
    for screen in data:
        print(f"  - {screen.get('screen_id')}: {len(screen.get('actions', []))} actions")
```

### Warning: "Low confidence scores"

**Nguyên nhân**: Actions xuất hiện trên ít screens

**Giải pháp**: Chạy exploration với nhiều screens hơn hoặc chấp nhận confidence thấp

### Warning: "Wrong domain detected"

**Nguyên nhân**: Auto-detection nhận diện sai domain

**Giải pháp**: Chỉ định domain cụ thể
```bash
python scripts/run_task_synthesis.py \
    --input data/raw/site \
    --output data/tasks/site \
    --domain ecommerce  # Chỉ định rõ domain
```

## Tips & Best Practices

### 1. Kiểm tra exploration results trước

```bash
# Xem có bao nhiêu screens và actions
python -c "
import json
with open('data/raw/agenttrek/screens.json') as f:
    data = json.load(f)
    print(f'Screens: {len(data)}')
    total_actions = sum(len(s.get('actions', [])) for s in data)
    print(f'Total actions: {total_actions}')
"
```

### 2. Thử auto-detection trước

Luôn thử auto-detection trước, sau đó mới chỉ định domain nếu cần:

```bash
# Bước 1: Auto-detection
python scripts/run_task_synthesis.py -i data/raw/site -o data/tasks/site

# Bước 2: Xem kết quả
cat data/tasks/site/tasks_summary.txt

# Bước 3: Nếu không OK, chỉ định domain
python scripts/run_task_synthesis.py -i data/raw/site -o data/tasks/site -d ecommerce
```

### 3. Sử dụng custom patterns cho domain đặc biệt

```python
from exploration import TaskSynthesizer

custom_patterns = [
    (['book', 'reserve'], "book appointment", "Book service"),
    (['cancel'], "cancel booking", "Cancel reservation"),
]

synthesizer = TaskSynthesizer(custom_patterns=custom_patterns)
task_graph = synthesizer.synthesize(screens)
```

### 4. Batch processing nhiều sites

```bash
#!/bin/bash
# Chạy task synthesis cho nhiều sites

for site_dir in data/raw/*/; do
    site_name=$(basename "$site_dir")
    echo "Processing: $site_name"
    
    python scripts/run_task_synthesis.py \
        --input "$site_dir" \
        --output "data/tasks/$site_name"
done
```

## Tích hợp vào pipeline

### Makefile

```makefile
# Phase 3: Task Synthesis
task-synthesis:
    python scripts/run_task_synthesis.py \
        --input data/raw/$(SITE) \
        --output data/tasks/$(SITE) \
        --domain $(DOMAIN)

# Ví dụ: make task-synthesis SITE=agenttrek DOMAIN=ecommerce
```

### Shell script

```bash
#!/bin/bash
# run_phase3.sh

INPUT_DIR=${1:-"data/raw/agenttrek"}
OUTPUT_DIR=${2:-"data/tasks/agenttrek"}
DOMAIN=${3:-"auto"}

if [ "$DOMAIN" = "auto" ]; then
    python scripts/run_task_synthesis.py -i "$INPUT_DIR" -o "$OUTPUT_DIR"
else
    python scripts/run_task_synthesis.py -i "$INPUT_DIR" -o "$OUTPUT_DIR" -d "$DOMAIN"
fi

# Usage:
# ./run_phase3.sh data/raw/agenttrek data/tasks/agenttrek ecommerce
```

## Kiểm tra kết quả

### 1. Xem summary

```bash
cat data/tasks/agenttrek/tasks_summary.txt
```

### 2. Phân tích tasks

```python
import json

with open("data/tasks/agenttrek/tasks.json") as f:
    data = json.load(f)

print(f"Total tasks: {len(data['tasks'])}")

# Group by priority
from collections import Counter
priorities = Counter(t['priority'] for t in data['tasks'])
print(f"By priority: {priorities}")

# Average confidence
avg_conf = sum(t['confidence'] for t in data['tasks']) / len(data['tasks'])
print(f"Average confidence: {avg_conf:.2f}")
```

### 3. Visualize (optional)

```python
import matplotlib.pyplot as plt
import json

with open("data/tasks/agenttrek/tasks.json") as f:
    data = json.load(f)

# Plot confidence distribution
confidences = [t['confidence'] for t in data['tasks']]
plt.hist(confidences, bins=10)
plt.xlabel('Confidence')
plt.ylabel('Number of Tasks')
plt.title('Task Confidence Distribution')
plt.savefig('task_confidence.png')
```

## Next Steps

Sau khi có tasks.json, bạn có thể:

1. **Phase 4**: Thực thi tasks (Task Execution)
2. **Training**: Sử dụng tasks để train agent
3. **Evaluation**: Đánh giá agent trên các tasks
4. **Analysis**: Phân tích task complexity, coverage, etc.

## Tham khảo

- [TASK_SYNTHESIS.md](TASK_SYNTHESIS.md) - Chi tiết về Task Synthesis
- [QUICKSTART_TASK_SYNTHESIS.md](QUICKSTART_TASK_SYNTHESIS.md) - Quick start guide
- [examples/task_synthesis_example.py](../examples/task_synthesis_example.py) - Code examples
