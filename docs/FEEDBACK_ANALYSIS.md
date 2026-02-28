# Phân Tích Feedback và Đề Xuất Điều Chỉnh

## 📝 Feedback từ Giáo sư Vũ

### Định hướng đúng mà giáo sư đề ra:

**Phase 1: Exploration (LLM khám phá)**
- LLM explore website
- Vừa khám phá vừa **execute** để lưu "vết"
- Lưu paths với data: screen (DOM/URL), action, object (locator), data entered
- Format: JSON hoặc text
- **Độ chính xác không phải tối quan trọng**

**Phase 2: Task Synthesis**
- Từ các paths đã khám phá
- **LLM tạo tasks và descriptions**
- **"Không cần grounding gì cả"**

**Phase 3: Task Validation**
- **LLM đi lại các tasks**
- Loại bỏ những task không execute được
- → Được data sạch cho SLM học

**Phase 4: Train SLM**

**Phase 5: Evaluate SLM**

---

## 🔍 Phân Tích Hiện Trạng

### ✅ Những gì đang đúng hướng:

1. **Phase 1 (Exploration)** - ✅ Đúng hướng
   - Có `exploration/exploration_bridge.py` - BFS exploration loop
   - Có adapters cho external explorers (AgentTrek, WebTactix)
   - Lưu screens, actions (cả semantic + executable), transitions
   - Format: JSON/JSONL
   - **Location**: `data/raw/{explorer_name}/`

2. **Phase 4 (Training)** - ✅ Đã có
   - Module `training/` với train.py, model.py, dataset.py
   - Có thể train SLM từ trajectories

3. **Phase 5 (Evaluation)** - ✅ Đã có
   - Module `agents/` với SLMAgent, SimpleAgent
   - Có runner.py để execute và evaluate

### ❌ Những gì SAI HƯỚNG hoặc CẦN ĐIỀU CHỈNH:

#### 1. **Phase 2: Task Synthesis** - ⚠️ Cần điều chỉnh lớn

**Hiện tại:**
```python
# exploration/task_synthesis.py
class TaskSynthesizer:
    """
    Task Synthesis: Deterministic task inference from semantic actions.

    PURPOSE:
    - Aggregate semantic actions across screens
    - Infer high-level user tasks (workflows) deterministically
    - Group related actions into multi-step user goals
    - NO LLM calls - pure algorithmic approach  ⚠️ VẤN ĐỀ Ở ĐÂY!
    """
```

**Vấn đề:**
- Đang dùng **thuật toán deterministic** thay vì LLM
- Không có LLM generate task descriptions
- Quá focus vào "semantic/executable separation"

**Giáo sư muốn:**
- **LLM đọc paths và TẠO tasks + descriptions**
- Không cần "grounding" hay thuật toán phức tạp
- Đơn giản: đưa paths cho LLM, LLM tổng hợp thành tasks

#### 2. **ActionGrounder** - ⚠️ KHÔNG CẦN THIẾT (theo feedback)

**Hiện tại:**
```python
# exploration/action_grounder.py
class ActionGrounder:
    """
    Maps semantic action intents to executable actions.
    PHASE USAGE: Phase 4 (Task Execution)
    """
```

**Vấn đề:**
- Phase 1 đã lưu cả semantic + executable rồi
- Không cần "ground" lại trong Phase 2
- Giáo sư nói rõ: "Step 2 không cần grounding gì cả"

**ActionGrounder dùng ở đâu:**
- Có thể dùng trong Phase 3 (Task Validation) khi LLM cần execute lại
- KHÔNG dùng trong Phase 2 (Task Synthesis)

#### 3. **Phase 3: Task Validation** - ⚠️ THIẾU

**Hiện tại:**
- KHÔNG có module nào implement Phase 3 như giáo sư mô tả
- Không có logic "LLM đi lại tasks và loại bỏ task fail"

**Giáo sư muốn:**
- LLM **execute lại từng task** đã tạo ở Phase 2
- Nếu task execute thành công → giữ lại
- Nếu task fail → loại bỏ
- → Data cuối cùng là "validated tasks" cho SLM học

---

## 🎯 Đề Xuất Điều Chỉnh

### Roadmap điều chỉnh theo feedback:

### ✅ Phase 1: Exploration - GIỮ NGUYÊN
**Không cần thay đổi gì**
- Đã đúng: LLM explore, execute, lưu paths
- Có adapters cho external explorers
- Output: `data/raw/{explorer}/` với screens, actions, transitions

### 🔄 Phase 2: Task Synthesis - THAY ĐỔI LỚN

**Cần làm:**

1. **Viết lại `TaskSynthesizer` để dùng LLM**
   ```python
   class LLMTaskSynthesizer:
       """
       LLM-based task synthesis from exploration paths.

       Input: Paths from Phase 1 (screens, actions, transitions)
       Process: LLM reads paths and generates task descriptions
       Output: List of tasks with descriptions
       """

       def synthesize_tasks(self, paths: List[Path]) -> List[Task]:
           # 1. Format paths thành prompt
           prompt = self._format_paths_for_llm(paths)

           # 2. Gọi LLM để tạo tasks
           llm_response = self.llm.generate(prompt)

           # 3. Parse tasks từ LLM response
           tasks = self._parse_tasks(llm_response)

           return tasks
   ```

2. **Đơn giản hóa - Không cần:**
   - Semantic/executable separation quá nghiêm ngặt trong phase này
   - Deterministic algorithms
   - Complex pattern matching

3. **Cần có:**
   - LLM prompt template để generate tasks
   - Parser để extract tasks từ LLM response
   - Simple validation (format check)

**Output Phase 2:**
```json
{
  "tasks": [
    {
      "task_id": "task_1",
      "description": "User searches for a product",
      "steps": [
        "Navigate to homepage",
        "Enter search query in search box",
        "Click search button",
        "View search results"
      ],
      "path": ["screen_1", "screen_2", "screen_3"],
      "actions": ["action_1", "action_2", "action_3"]
    }
  ]
}
```

### ➕ Phase 3: Task Validation - TẠO MỚI

**Cần tạo module mới: `exploration/task_validation.py`**

```python
class TaskValidator:
    """
    Validates tasks by executing them with LLM.

    Phase 3: Execute tasks generated in Phase 2
    Keep tasks that succeed, discard tasks that fail.
    """

    def __init__(self, env, llm_agent):
        self.env = env
        self.llm_agent = llm_agent

    def validate_tasks(self, tasks: List[Task]) -> List[ValidatedTask]:
        validated = []

        for task in tasks:
            try:
                # LLM thực thi task
                success = self._execute_task(task)

                if success:
                    validated.append(task)
                    logger.info(f"✅ Task {task.task_id} validated")
                else:
                    logger.info(f"❌ Task {task.task_id} failed")

            except Exception as e:
                logger.warning(f"⚠️ Task {task.task_id} error: {e}")

        return validated

    def _execute_task(self, task: Task) -> bool:
        """Execute task with LLM agent."""
        # Reset environment
        self.env.reset()

        # LLM executes each step
        for step in task.steps:
            action = self.llm_agent.decide(step)
            obs, done = self.env.step(action)

            if done or self._is_stuck():
                return False

        return True
```

**Output Phase 3:**
```json
{
  "validated_tasks": [...],  // Tasks that executed successfully
  "failed_tasks": [...],     // Tasks that failed (for analysis)
  "validation_stats": {
    "total": 50,
    "passed": 35,
    "failed": 15,
    "success_rate": 0.7
  }
}
```

### ✅ Phase 4: Training - GIỮ NGUYÊN
- Dùng validated tasks làm input
- Module `training/` đã có sẵn

### ✅ Phase 5: Evaluation - GIỮ NGUYÊN
- Module `agents/` đã có sẵn

---

## 📋 Action Items - Ưu tiên cao

### Tuần 1: Refactor Phase 2 (Task Synthesis)

1. **Tạo `LLMTaskSynthesizer`**
   - [ ] File mới: `exploration/llm_task_synthesizer.py`
   - [ ] LLM prompt templates
   - [ ] Parser cho LLM responses
   - [ ] Integration test

2. **Cập nhật `run_exploration.py`**
   - [ ] Replace `TaskSynthesizer` → `LLMTaskSynthesizer`
   - [ ] Update CLI arguments
   - [ ] Update documentation

3. **Deprecated old code**
   - [ ] Đánh dấu `task_synthesis.py` (deterministic) là deprecated
   - [ ] Keep code để reference nếu cần

### Tuần 2: Implement Phase 3 (Task Validation)

1. **Tạo `TaskValidator`**
   - [ ] File mới: `exploration/task_validator.py`
   - [ ] Task execution logic
   - [ ] Success/failure detection
   - [ ] Validation metrics

2. **Tích hợp vào pipeline**
   - [ ] Update `run_exploration.py` để chạy Phase 3
   - [ ] CLI: `--skip-validation` option
   - [ ] Progress tracking và logging

3. **Testing**
   - [ ] Unit tests cho validator
   - [ ] Integration test cho full pipeline
   - [ ] Test với real website

### Tuần 3: Documentation & Clean up

1. **Cập nhật documentation**
   - [ ] Update `PROJECT_CONTEXT.md`
   - [ ] Update `docs/PHASE3_WORKFLOW.md` → `docs/PHASE2_3_WORKFLOW.md`
   - [ ] Viết mới `docs/LLM_TASK_SYNTHESIS.md`
   - [ ] Update `README.md`

2. **Clean up code**
   - [ ] Remove hoặc archive `action_grounder.py` (nếu không dùng)
   - [ ] Refactor semantic/executable separation (relax rules)
   - [ ] Code review và optimization

3. **Examples & Demos**
   - [ ] Example notebook: Full pipeline Phase 1-5
   - [ ] Demo video hoặc screenshots
   - [ ] Sample output data

---

## 🎨 Architecture Mới (Sau điều chỉnh)

```
┌─────────────────────────────────────────────────────────┐
│ Phase 1: LLM Exploration                                │
│ - LLM explores website                                  │
│ - Execute actions and save "traces"                     │
│ - Output: paths (screens, actions, transitions)        │
│ - Location: data/raw/{explorer}/                       │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 2: LLM Task Synthesis                            │
│ - LLM reads exploration paths                           │
│ - Generate task descriptions                            │
│ - NO grounding, NO complex algorithms                   │
│ - Output: tasks with descriptions                       │
│ - Location: data/tasks/{explorer}/tasks.json           │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 3: LLM Task Validation [NEW!]                    │
│ - LLM executes each task                                │
│ - Keep successful tasks, discard failed ones            │
│ - Output: validated tasks for training                  │
│ - Location: data/validated/{explorer}/                 │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 4: Train SLM                                      │
│ - Use validated tasks as training data                  │
│ - Train small language model                            │
│ - Output: trained model weights                         │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 5: Evaluate SLM                                   │
│ - Test SLM on validation tasks                          │
│ - Measure success rate, efficiency                      │
│ - Output: evaluation metrics                            │
└─────────────────────────────────────────────────────────┘
```

---

## 💡 Key Insights từ Feedback

1. **Đơn giản hóa Phase 2**
   - Hiện tại quá complicated với algorithmic approach
   - Giáo sư muốn: LLM đọc → LLM viết tasks → Done
   - "Không cần grounding" = không cần mapping phức tạp

2. **Phase 3 là key để có data sạch**
   - Validation phase lọc bỏ bad tasks
   - Đây là step quan trọng trước training
   - Đảm bảo SLM học từ data "có thể thực thi được"

3. **Độ chính xác Phase 1 không quan trọng**
   - Phase 3 sẽ filter lại
   - Focus vào coverage (khám phá nhiều) hơn accuracy

4. **Tách biệt LLM và SLM rõ ràng**
   - Phase 1-3: LLM (expensive, offline)
   - Phase 5: SLM (cheap, production)
   - Training bridge giữa hai worlds

---

## 🚀 Next Steps

### Immediate (Ngay lập tức):

1. **Meeting với team**
   - Discuss feedback này
   - Align understanding về 5 phases
   - Phân công tasks

2. **Prototype Phase 2 mới**
   - Viết quick prototype cho LLMTaskSynthesizer
   - Test với 1-2 examples từ Phase 1 data
   - Validate approach trước khi implement full

3. **Design Phase 3**
   - Viết design doc cho TaskValidator
   - Xác định success/failure criteria
   - Plan integration với existing code

### Trước khi meeting với thầy:

1. **Prepare demo**
   - Show current Phase 1 output
   - Prototype Phase 2 (LLM-based)
   - Mock Phase 3 flow

2. **Questions list**
   - Clarify validation criteria cho Phase 3
   - LLM choice (GPT-4? Claude?)
   - Budget considerations

3. **Updated plan**
   - Timeline chi tiết cho Phase 2, 3
   - Resource requirements
   - Risk mitigation

---

## 📊 Estimated Effort

### Phase 2 Refactor:
- LLMTaskSynthesizer: **3-4 days**
- Testing & Integration: **2-3 days**
- Documentation: **1-2 days**
- **Total: ~1.5 weeks**

### Phase 3 Implementation:
- TaskValidator core: **4-5 days**
- Integration & Testing: **3-4 days**
- Optimization: **2-3 days**
- **Total: ~2 weeks**

### Documentation & Polish:
- Update all docs: **2-3 days**
- Examples & demos: **2-3 days**
- **Total: ~1 week**

**Grand Total: ~4-5 weeks để hoàn thành điều chỉnh**

---

## 🎯 Success Metrics

### Phase 2 (Task Synthesis):
- [ ] LLM successfully generates task descriptions
- [ ] Tasks are human-readable and make sense
- [ ] 80%+ of generated tasks are "reasonable"

### Phase 3 (Task Validation):
- [ ] Can execute tasks automatically
- [ ] Clear success/failure detection
- [ ] 50%+ validation success rate (tunable)

### Training (Phase 4):
- [ ] SLM can train on validated data
- [ ] Training converges properly
- [ ] Reasonable loss curves

### Evaluation (Phase 5):
- [ ] SLM can execute some tasks
- [ ] Better than random baseline
- [ ] Measurable progress over iterations

---

**Prepared by:** AI Assistant
**Date:** March 1, 2026
**Status:** Awaiting team review and professor feedback
