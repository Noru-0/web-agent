# Output Schema - Chi tiết định dạng output của mỗi Phase

**Ngày**: March 4, 2026
**Mục đích**: Tài liệu đầy đủ về cấu trúc và định dạng dữ liệu output của ba phase

---

## Tổng Quan

```
PHASE          INPUT FORMAT              OUTPUT FORMAT           LOCATION
═════════════════════════════════════════════════════════════════════════════
Phase 1        URL                       ExplorationResult       data/raw/{domain}/
Exploration    https://example.com       (JSON files)            ├─ screens.jsonl
               (bắt đầu tại URL)         • screens              ├─ actions.jsonl
                                         • actions               └─ transitions.jsonl
                                         • transitions

Phase 2        ExplorationResult         SynthesizedTask list    data/tasks/{domain}/
Task Gen       (Screens + Actions)       (JSON file)             ├─ tasks_llm.json
               từ Phase 1                [task_1, task_2, ...]  └─ tasks_llm_summary.txt

Phase 3        SynthesizedTask list      ValidationReport        data/tasks/{domain}/
Validation     từ Phase 2                + Clean task list       ├─ validation_report.json
               [task_1, task_2, ...]    [task_1, task_3, ...]  └─ tasks_validated.json
```

---

## Phase 1: Exploration Output

**Thư mục lưu trữ**: `data/raw/{domain_folder}/`

Ví dụ:
- `data/raw/example.com/`
- `data/raw/localhost_9999/`
- `data/raw/shop.example.com/`

### 1.1. Screens Output - `screens.jsonl`

**Format**: JSONL (một JSON object trên mỗi dòng)

```json
{
  "screen_id": "a1b2c3d4e5f6",
  "url": "https://example.com/products",
  "dom_snapshot": "<div>...</div>",
  "visible_text": "Browse our products. We offer...",
  "semantic_summary": "Product listing page with product cards and filters",
  "screen_type": "listing",
  "timestamp": "2026-03-04T10:30:45.123456",
  "screenshot": null,
  "dom_fingerprint": "example.com/products::a1b2c3::f4e5d6",
  "meta": {
    "source_url": "https://example.com/products",
    "detected_language": "en",
    "page_title": "Our Products"
  }
}
```

**Field Chi tiết**:
| Field              | Type         | Mô tả                                                                         |
| ------------------ | ------------ | ----------------------------------------------------------------------------- |
| `screen_id`        | string       | ID duy nhất của màn hình (SHA256 hash)                                        |
| `url`              | string       | URL của màn hình                                                              |
| `dom_snapshot`     | string       | HTML/DOM của trang (cleaned)                                                  |
| `visible_text`     | string       | Văn bản hiển thị trên trang                                                   |
| `semantic_summary` | string       | Tóm tắt ngữ nghĩa (LLM tạo)                                                   |
| `screen_type`      | string       | Loại màn hình: `homepage`, `listing`, `product_detail`, `form`, `login`, v.v. |
| `timestamp`        | ISO8601      | Khi màn hình được ghi lại                                                     |
| `screenshot`       | string\|null | Base64 screenshot (tùy chọn)                                                  |
| `dom_fingerprint`  | string       | Fingerprint để deduplication                                                  |
| `meta`             | object       | Metadata bổ sung                                                              |

### 1.2. Actions Output - `actions.jsonl`

**Format**: JSONL (mỗi dòng là 1 action)

```json
{
  "action_id": "act_f1e2d3c4b5a6",
  "action_type": "click",
  "source_screen_id": "a1b2c3d4e5f6",
  "semantic": {
    "intent": "view",
    "object": "product details",
    "context": "via product card",
    "description": "click on product card to view details",
    "confidence": 0.92,
    "action_id": "act_f1e2d3c4b5a6",
    "grounding_hints": {
      "target_role": ["product_link", "product_card"],
      "element_affordance": ["click"],
      "keywords": ["product", "view", "details"],
      "exclude_keywords": ["cart", "wishlist"],
      "preferred_region": ["main_content"],
      "interaction_order": "initial"
    }
  },
  "executable": {
    "selector": "a.product-card",
    "xpath": "//a[@class='product-card']",
    "coordinates": [245, 150],
    "dom_path": "body > div#main > section > div.products > a",
    "element_id": "prod_123",
    "input_value": null
  },
  "meta": {
    "interaction_type": "dom_click",
    "confidence": 0.85,
    "locator_found": true
  }
}
```

**Semantic Fields** (để LLM dùng):
```json
{
  "intent": "view | click | fill | search | navigate | submit | ...",
  "object": "product card | search box | login button | ...",
  "context": "optional additional meaning",
  "description": "Natural language description",
  "confidence": 0.0 - 1.0,
  "grounding_hints": {
    "target_role": ["role1", "role2"],         // Resource roles
    "element_affordance": ["click", "drag"],    // DOM affordances
    "keywords": ["word1", "word2"],             // Text keywords
    "exclude_keywords": ["bad1", "bad2"],       // Exclude patterns
    "preferred_region": ["main_content"],       // Visual regions
    "interaction_order": "initial | follow-up"  // Interaction sequence
  }
}
```

**Executable Fields** (LLM không được dùng):
```json
{
  "selector": "CSS selector",
  "xpath": "XPath expression",
  "coordinates": [x, y],                    // Screen coordinates
  "dom_path": "Document tree path",
  "element_id": "HTML element id or data-id",
  "input_value": "text input value"
}
```

### 1.3. Transitions Output - `transitions.jsonl`

**Format**: JSONL (mỗi dòng là 1 transition)

```json
{
  "transition_id": "trans_a1b2c3d4e5f6",
  "from_screen_id": "a1b2c3d4e5f6",
  "action_id": "act_f1e2d3c4b5a6",
  "to_screen_id": "b2c3d4e5f6a1",
  "success": true,
  "meta": {
    "time_taken_ms": 342,
    "page_changed": true,
    "url_changed": false,
    "dom_changed": true
  }
}
```

**Field Chi tiết**:
| Field            | Mô tả                                    |
| ---------------- | ---------------------------------------- |
| `transition_id`  | ID duy nhất của transition               |
| `from_screen_id` | Screen ID ban đầu                        |
| `action_id`      | ID (reference) của action được thực hiện |
| `to_screen_id`   | Screen ID đích                           |
| `success`        | True nếu transition thành công           |
| `meta`           | Metadata (thời gian, thay đổi DOM, v.v.) |

### 1.4. Metadata - `metadata.json`

```json
{
  "explorer_name": "example.com",
  "start_url": "https://example.com",
  "timestamp": "2026-03-04T10:30:45.123456",
  "statistics": {
    "total_screens": 47,
    "total_actions": 128,
    "total_transitions": 184,
    "exploration_duration_seconds": 342,
    "unique_screen_fingerprints": 42
  },
  "config": {
    "max_screens": 50,
    "max_transitions": 200,
    "max_actions_per_screen": 10,
    "deduplication_enabled": true
  }
}
```

---

## Phase 2: Task Generation Output

**Thư mục lưu trữ**: `data/tasks/{domain_folder}/`

Ví dụ:
- `data/tasks/example.com/`
- `data/tasks/localhost_9999/`

### 2.1. Tasks Output - `tasks_llm.json`

**Format**: JSON (structured array)

```json
{
  "tasks": [
    {
      "task_id": "task_1",
      "name": "Browse Product Catalog",
      "description": "The user wants to explore available products in the online store and view product details.",
      "steps": [
        {
          "step_number": 1,
          "description": "Navigate to the products page",
          "screen_id": "screen_0",
          "action_id": "action_1"
        },
        {
          "step_number": 2,
          "description": "View a specific product's details by clicking on it",
          "screen_id": "screen_1",
          "action_id": "action_5"
        },
        {
          "step_number": 3,
          "description": "Review the product description and specifications",
          "screen_id": "screen_2",
          "action_id": null
        }
      ],
      "confidence": 0.94,
      "category": "navigation"
    },
    {
      "task_id": "task_2",
      "name": "Search for Specific Product",
      "description": "The user searches for a specific product using the search functionality.",
      "steps": [
        {
          "step_number": 1,
          "description": "Focus on the search input field",
          "screen_id": "screen_0",
          "action_id": "action_8"
        },
        {
          "step_number": 2,
          "description": "Type the product name in the search box",
          "screen_id": "screen_0",
          "action_id": "action_9"
        },
        {
          "step_number": 3,
          "description": "Submit the search query",
          "screen_id": "screen_0",
          "action_id": "action_10"
        },
        {
          "step_number": 4,
          "description": "View search results",
          "screen_id": "screen_3",
          "action_id": null
        }
      ],
      "confidence": 0.88,
      "category": "search"
    },
    {
      "task_id": "task_3",
      "name": "Add Product to Cart",
      "description": "The user selects and adds a product to their shopping cart.",
      "steps": [
        {
          "step_number": 1,
          "description": "View product details",
          "screen_id": "screen_2",
          "action_id": null
        },
        {
          "step_number": 2,
          "description": "Click the 'Add to Cart' button",
          "screen_id": "screen_2",
          "action_id": "action_15"
        },
        {
          "step_number": 3,
          "description": "Confirm product added to cart",
          "screen_id": "screen_4",
          "action_id": null
        }
      ],
      "confidence": 0.96,
      "category": "transaction"
    }
  ],
  "metadata": {
    "total_tasks": 3,
    "synthesizer": "LLMTaskSynthesizer",
    "llm_provider": "openai",
    "model": "gpt-4-turbo-preview",
    "temperature": 0.7,
    "timestamp": "2026-03-04T10:35:22.456789"
  }
}
```

**Task Structure**:
```json
{
  "task_id": "task_N",                      // Unique ID
  "name": "user-friendly task name",        // Ngắn, mô tả
  "description": "detailed task description", // Chi tiết what/why/how
  "steps": [
    {
      "step_number": 1,
      "description": "what to do",
      "screen_id": "screen_id or null",
      "action_id": "action_id or null"
    }
  ],
  "confidence": 0.0 - 1.0,                 // LLM confidence
  "category": "navigation|search|transaction|content|form|..."
}
```

**Task Categories**:
- `navigation` - Chuyển trang, click links
- `search` - Tìm kiếm nội dung
- `transaction` - Mua hàng, thanh toán
- `content` - Đọc, xem nội dung
- `form` - Điền form, nhập thông tin
- `account` - Login, profile management
- `general` - Khác

### 2.2. Summary Output - `tasks_llm_summary.txt`

```
Task Synthesis Summary Report
═════════════════════════════════════════════

Website: https://example.com
Exploration Stats:
  - Screens discovered: 47
  - Actions recorded: 128
  - Transitions captured: 184

Task Synthesis Stats:
  - LLM Provider: OpenAI
  - Model: gpt-4-turbo-preview
  - Synthesis Method: LLMTaskSynthesizer
  - Temperature: 0.7
  - Max Tokens: 4000

Generated Tasks: 3
  Task 1: Browse Product Catalog (confidence: 0.94)
    - 3 steps
    - Category: navigation

  Task 2: Search for Specific Product (confidence: 0.88)
    - 4 steps
    - Category: search

  Task 3: Add Product to Cart (confidence: 0.96)
    - 3 steps
    - Category: transaction

Timestamp: 2026-03-04T10:35:22.456789
Synthesis Duration: 5.32 seconds
```

---

## Phase 3: Task Validation Output

**Thư mục lưu trữ**: `data/tasks/{domain_folder}/`

### 3.1. Validation Report - `validation_report.json`

```json
{
  "total_tasks": 3,
  "validated_tasks": 2,
  "failed_tasks": 1,
  "success_rate": 0.6667,
  "validation_results": [
    {
      "task_id": "task_1",
      "task_name": "Browse Product Catalog",
      "success": true,
      "failure_reason": null,
      "execution_time": 2.45,
      "steps_completed": 3,
      "total_steps": 3
    },
    {
      "task_id": "task_2",
      "task_name": "Search for Specific Product",
      "success": false,
      "failure_reason": "Stuck at step 2: search input not responding",
      "execution_time": 8.12,
      "steps_completed": 1,
      "total_steps": 4
    },
    {
      "task_id": "task_3",
      "task_name": "Add Product to Cart",
      "success": true,
      "failure_reason": null,
      "execution_time": 3.78,
      "steps_completed": 3,
      "total_steps": 3
    }
  ],
  "timestamp": "2026-03-04T10:40:15.789012",
  "validation_duration_seconds": 14.35,
  "config": {
    "max_steps_per_task": 20,
    "timeout_per_task": 60,
    "stuck_detection_window": 3
  }
}
```

**ValidationResult Structure**:
```json
{
  "task_id": "task_id",
  "task_name": "task name",
  "success": true|false,
  "failure_reason": null|"string describing why failed",
  "execution_time": 2.45,              // seconds
  "steps_completed": 3,                // số steps thành công
  "total_steps": 3                     // tổng số steps
}
```

**Failure Reasons**:
- `"Stuck at step N: state not changing"` - Môi trường không thay đổi
- `"Action failed: selector not found"` - Không tìm thấy element
- `"Timeout exceeded"` - Vượt quá timeout
- `"Invalid action: type not supported"` - Action không hợp lệ
- `"Environment error: <error message>"` - Lỗi môi trường

### 3.2. Validated Tasks - `tasks_validated.json`

**Format**: Giống Phase 2 nhưng chỉ chứa tasks thành công

```json
{
  "tasks": [
    {
      "task_id": "task_1",
      "name": "Browse Product Catalog",
      "description": "The user wants to explore available products...",
      "steps": [...],
      "confidence": 0.94,
      "category": "navigation"
    },
    {
      "task_id": "task_3",
      "name": "Add Product to Cart",
      "description": "The user selects and adds a product...",
      "steps": [...],
      "confidence": 0.96,
      "category": "transaction"
    }
  ],
  "metadata": {
    "total_tasks": 2,
    "validation_source": "validation_report.json",
    "validation_timestamp": "2026-03-04T10:40:15.789012",
    "success_rate": 0.6667,
    "note": "Filtered to include only successfully validated tasks"
  }
}
```

### 3.3. Validation Summary - `validation_summary.txt`

```
Task Validation Summary Report
═════════════════════════════════════════════

Validation Session: 2026-03-04T10:40:15.789012

Input: 3 tasks from Phase 2
Output: 2 validated tasks (66.7% success rate)

Validation Results:
─────────────────────────────────────────────

✅ PASS: Task 1 - Browse Product Catalog
   Duration: 2.45 sec
   Steps: 3/3 completed

❌ FAIL: Task 2 - Search for Specific Product
   Duration: 8.12 sec
   Steps: 1/4 completed
   Reason: Stuck at step 2 (search input not responding)

✅ PASS: Task 3 - Add Product to Cart
   Duration: 3.78 sec
   Steps: 3/3 completed

─────────────────────────────────────────────

Statistics:
  - Total validation time: 14.35 seconds
  - Success rate: 66.7% (2/3)
  - Average execution time: 4.78 seconds
  - Tasks kept: 2
  - Tasks filtered out: 1

Next Step:
  ✅ tasks_validated.json is ready for Phase 4 (SLM Training)

Config:
  - Max steps per task: 20
  - Task timeout: 60 seconds
  - Stuck detection window: 3 steps
```

---

## Complete Example: End-to-End Data Flow

### Step 1: Phase 1 Exploration

**Input URL**: `https://example.com`

**Output Files**:
```
data/raw/example.com/
├─ screens.jsonl         (47 screens)
├─ actions.jsonl         (128 actions)
├─ transitions.jsonl     (184 transitions)
└─ metadata.json         (statistics)
```

**Example Screen (1 dòng từ screens.jsonl)**:
```json
{"screen_id": "abc123", "url": "https://example.com", "visible_text": "Browse our products...", ...}
```

### Step 2: Phase 2 Task Synthesis

**Input**: `data/raw/example.com/` (screens + actions)

**LLM Prompt** (simplified):
```
Here are 47 screens discovered on https://example.com:
- Screen 1: Homepage with products list
- Screen 2: Product detail page
- Screen 3: Shopping cart
- ...

And 128 actions that can be performed:
- Click product link
- Add to cart
- Search for product
- ...

Generate 3-5 realistic user tasks with step-by-step descriptions.
```

**LLM Response** (structured):
```
Task 1: Browse Product Catalog
- Step 1: Click on products link
- Step 2: Click on a product card
- Step 3: Read product details

Task 2: Search for Product
- Step 1: Click search box
- Step 2: Type product name
- Step 3: Submit search
- Step 4: View results

Task 3: Add to Cart
- Step 1: View product details
- Step 2: Click add to cart
- Step 3: Confirm
```

**Output Files**:
```
data/tasks/example.com/
├─ tasks_llm.json           (3 tasks)
└─ tasks_llm_summary.txt
```

### Step 3: Phase 3 Validation

**Input**: `data/tasks/example.com/tasks_llm.json` (3 tasks)

**Validation Process**:
```
For each task:
  Task 1: ✅ PASS (all 3 steps executed)
  Task 2: ❌ FAIL (stuck at step 2)
  Task 3: ✅ PASS (all 3 steps executed)

Filter: Keep only successful (Task 1, 3)
```

**Output Files**:
```
data/tasks/example.com/
├─ tasks_llm.json            (original 3 tasks, Phase 2 output)
├─ validation_report.json    (detailed results)
├─ tasks_validated.json      (2 clean tasks for training)
└─ validation_summary.txt
```

---

## Data Size Estimates

| Component             | Items                                      | File Size  | Notes                 |
| --------------------- | ------------------------------------------ | ---------- | --------------------- |
| 1 Screen              | 1                                          | ~2-5 KB    | DOM + text + metadata |
| 1 Action              | 1                                          | ~1-2 KB    | Semantic + executable |
| 1 Transition          | 1                                          | ~200 bytes | References only       |
| Phase 1 Complete      | 50 screens + 150 actions + 200 transitions | ~700 KB    | Typical exploration   |
| Phase 2 Tasks         | 5-10 tasks                                 | ~20-50 KB  | JSON structured       |
| Phase 3 Report        | Validation results                         | ~10-20 KB  | Metadata + results    |
| **Total per website** | -                                          | **~1 MB**  | After all 3 phases    |

---

## Key Design Patterns

### 1. JSONL for Streaming (Phase 1)

**Why JSONL?**
- Mỗi object là 1 dòng → dễ streaming
- Không cần load tất cả vào memory
- Dễ append (write-once)

```
✅ screens.jsonl
❌ screens.json (array - khó append)
```

### 2. Single Source of Truth for Actions

**Actions trong Phase 1**:
```
✅ Stored ONCE in actions.jsonl
✅ Referenced via action_id từ transitions
✅ Contains BOTH semantic + executable
```

**NOT**:
```
❌ Duplicated trong multiple files
❌ Embedded trong transitions
```

### 3. Semantic/Executable Separation

**Phase 2 Input (LLM)**: Chỉ semantic
```json
{
  "intent": "view product",
  "object": "product details",
  "confidence": 0.92
}
```

**Phase 1 Storage**: BOTH (executable không dùng)
```json
{
  "semantic": {...},
  "executable": {
    "selector": "a.product-card",
    "xpath": "//a[@class='product-card']"
  }
}
```

### 4. Confidence Scoring

**Phase 2**: LLM confidence khi sinh task
```json
{
  "task_id": "task_1",
  "confidence": 0.94     // High confidence
}
```

**Phase 3**: Validation success/failure
```json
{
  "success": true,        // Actually works
  "failure_reason": null
}
```

---

## Storage Locations Summary

```
PROJECT_ROOT/
└── data/
    ├── raw/
    │   └── {domain}/
    │       ├── screens.jsonl         [Phase 1 Output]
    │       ├── actions.jsonl         [Phase 1 Output]
    │       ├── transitions.jsonl     [Phase 1 Output]
    │       └── metadata.json         [Phase 1 Output]
    │
    └── tasks/
        └── {domain}/
            ├── tasks_llm.json        [Phase 2 Output]
            ├── tasks_llm_summary.txt [Phase 2 Output]
            ├── validation_report.json    [Phase 3 Output]
            ├── tasks_validated.json      [Phase 3 Output]
            └── validation_summary.txt    [Phase 3 Output]
```

---

## API Reference for Output Access

```python
# Load Phase 1 output
from exploration.storage import ExplorationStorage

storage = ExplorationStorage("example.com")
screens = storage.load_screens()      # List[Screen]
actions_map = storage.load_actions()  # Dict[id -> Action]
transitions = storage.load_transitions()  # List[Transition]

# Load Phase 2 output
import json
with open("data/tasks/example.com/tasks_llm.json") as f:
    data = json.load(f)
tasks = [SynthesizedTask(**t) for t in data["tasks"]]

# Load Phase 3 output
with open("data/tasks/example.com/validation_report.json") as f:
    report = ValidationReport(**json.load(f))
print(f"Success rate: {report.success_rate:.1%}")
```

---

**Kết luận**: Mỗi phase có output format chuẩn xác, dễ parse, và tối ưu cho việc chuyển tiếp sang phase tiếp theo. 📊
