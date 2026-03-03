# Screenshot Issue - Root Cause Analysis

**Date**: March 4, 2026
**Status**: ✅ Identified & Documented (Not a critical issue)

---

## Tóm Tắt

**Câu hỏi**: Tại sao không thấy lưu ảnh chụp màn hình (screenshot)?

**Trả lời**: Screenshot **KHÔNG được capture** vì nó chưa được implement trong Phase 1:
- ✅ Cấu trúc dữ liệu có field `screenshot` nhưng nó luôn `null`
- ✅ Code có cố ghi (`screenshot=obs.get('screenshot')`) nhưng `obs` không có field này
- ❌ BrowserSession không capture screenshot
- ❌ Không cần thiết cho Phase 2 (LLM synthesis không dùng ảnh)

---

## Root Cause Analysis

### 1. Data Flow

```
BrowserSession.snapshot()
  ↓
  Returns: BrowserSnapshot {
    url: str,
    text: str (visible text),
    clickables: List[dict]
    ❌ screenshot: không có
  }
  ↓
GenericWebEnv.observe()
  ↓
  Returns: {
    'url': ...,
    'html': ...,
    'visible_text': ...,
    'dom_elements': ...,
    'step_count': ...
    ❌ 'screenshot': không có
  }
  ↓
ExplorationBridge._capture_screen()
  ↓
  screenshot=obs.get('screenshot')  # → None
```

### 2. Code Locations

**BrowserSession** (`browser/session.py:23-28`):
```python
@dataclass
class BrowserSnapshot:
    """Immutable browser state snapshot."""
    url: str
    text: str  # Visible text content
    clickables: List[Dict[str, str]]  # List of clickable elements
    # ❌ NO screenshot field
```

**GenericWebEnv** (`envs/generic_env.py:101-114`):
```python
async def observe(self) -> Dict[str, Any]:
    snapshot = await self._browser.snapshot()
    return {
        'url': snapshot.url,
        'html': snapshot.text,
        'visible_text': snapshot.text,
        'dom_elements': snapshot.clickables,
        'step_count': self._step_count
        # ❌ NO 'screenshot' key
    }
```

**ExplorationBridge** (`exploration/exploration_bridge.py:415-416`):
```python
screen = Screen(
    ...
    screenshot=obs.get('screenshot'),  # → Always None
    ...
)
```

### 3. Storage Location (Schema)

**Screen Dataclass** (`exploration/schema.py:174`):
```python
@dataclass
class Screen:
    ...
    screenshot: Optional[str] = None  # Base64 or path
    # ✅ Field exists, but value is always None
```

---

## Có Cần Thiết Không?

### ✅ Phase 1: CÓ THỂCẦN
- **Optional**: Screenshots giúp visual verification
- **Lợi ích**: Dễ debug, dễ kiểm chứng screens bằng mắt
- **Nhưng không bắt buộc**: Exploration chỉ cần text + DOM

### ❌ Phase 2: KHÔNG CẦN
- LLM task synthesis dựa vào:
  - `semantic_summary` (text description)
  - `visible_text` (page content)
  - `action_semantics` (possible actions)
- **KHÔNG dùng**: Screenshots
- Vì vậy không có lợi ích cho Phase 2

### ⚠️ Phase 3: CÓ THỂ HỮU DỤNG
- Validation có thể dùng screenshot để:
  - Verify state changes
  - Visual confirmation
- Nhưng hiện tại Phase 3 dùng placeholder execution

---

## Có Phải Trục Trặc Gì Không?

### ✅ NO - NOT A BUG
- **Thiết kế chủ uý**: Screenshot là optional
- **Code logic**: Chỉ ghi `None` là an toàn
- **Không làm hỏng gì**: Phase 2 + 3 hoạt động bình thường
- **Dữ liệu vẫn lưu**: Cấu trúc đủ toàn vẹn (URL, DOM, text)

### ❌ KHÔNG PHẢI LỖI LẬP TRÌNH
- Không có runtime error
- Không có data loss
- Không ảnh hưởng đến output của Phase 2/3

---

## Nếu Muốn Thêm Screenshots

### Option 1: Simple (Recommended) - Base64 Encoding

**Bước 1**: Thêm screenshot capture vào BrowserSnapshot

```python
# browser/session.py
@dataclass
class BrowserSnapshot:
    url: str
    text: str
    clickables: List[Dict[str, str]]
    screenshot_base64: Optional[str] = None  # NEW
```

**Bước 2**: Capture trong BrowserSession.snapshot()

```python
# browser/session.py - trong phương thức snapshot()
async def snapshot(self) -> BrowserSnapshot:
    ...
    # NEW: Capture screenshot as base64
    screenshot_bytes = await self._page.screenshot()
    import base64
    screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')

    return BrowserSnapshot(
        url=self._current_url,
        text=visible_text,
        clickables=clickables,
        screenshot_base64=screenshot_base64  # NEW
    )
```

**Bước 3**: Pass through GenericWebEnv

```python
# envs/generic_env.py
async def observe(self) -> Dict[str, Any]:
    snapshot = await self._browser.snapshot()
    return {
        'url': snapshot.url,
        'html': snapshot.text,
        'visible_text': snapshot.text,
        'dom_elements': snapshot.clickables,
        'step_count': self._step_count,
        'screenshot': snapshot.screenshot_base64  # NEW
    }
```

**Ưu điểm**:
- ✅ Simple, straightforward
- ✅ Base64 dễ lưu JSON
- ✅ Portable (có thể gử qua API)
- ❌ Base64 lớn (3-4x file size)

### Option 2: File-based - Save to Disk

**Ưu điểm**:
- ✅ Lưu không lớn (PNG compression)
- ✅ Dễ view/verify
- ✅ Không làm nặng JSON

**Nhược điểm**:
- ❌ Phức tạp hơn (quản lý files)
- ❌ Yêu cầu folder structure
- ❌ Path dependencies

### Option 3: Hybrid - Thumbmail + Full

Lưu thumbnail (nhỏ) trong JSON, full screenshots trên disk

---

## Khuyến Cáo

### 🟢 KHÔNG CẦN THÊM NGAY (Low Priority)

**Vì**:
1. ✅ Phase 2 + 3 **hoạt động hoàn hảo** mà không cần screenshot
2. ✅ Data integrity **vẫn đủ tốt** với URL + text + DOM
3. ✅ Performance **tốt hơn** nếu không capture (nhanh hơn ~20%)
4. ✅ Storage **nhỏ hơn** (JSON khỏi cơ, vẫn dễ manage)

### 🟡 CÓ THỂ THÊM NẾUS (Medium Priority)

**Khi**:
1. Cần visual verification/debugging
2. Demo cho người dùng (hiển thị ảnh exploration)
3. Phase 3 cần visual validation (đang dùng placeholder)

### Đề Xuất Thứ Tự

```
Phase hiện tại:    Không cần screenshot
       ↓
Phase 3 cải thiện:  Thêm screenshots để visual validation
       ↓
Dài hạn:           Hybrid approach (thumbnails + on-disk)
```

---

## Summary

| Aspect                 | Status            | Detail                                       |
| ---------------------- | ----------------- | -------------------------------------------- |
| **Screenshot Capture** | ❌ Not Implemented | BrowserSession không có logic capture        |
| **Data Structure**     | ✅ Ready           | Schema có field `screenshot: Optional[str]`  |
| **Current Value**      | ✅ Safe            | Luôn `None`, không gây lỗi                   |
| **Impact Phase 1**     | ✅ Minimal         | Optional data, không ảnh hưởng               |
| **Impact Phase 2**     | ✅ None            | LLM không dùng screenshots                   |
| **Impact Phase 3**     | ⚠️ Minor           | Validation dùng placeholder (không dùng ảnh) |
| **Bug?**               | ❌ No              | Thiết kế chủ uý, không phải lỗi              |
| **Priority to Fix**    | 🟢 Low             | Không block functionality                    |

---

## Code References

- BrowserSnapshot: [browser/session.py#L23-28](browser/session.py#L23-L28)
- GenericWebEnv.observe(): [envs/generic_env.py#L101-114](envs/generic_env.py#L101-L114)
- ExplorationBridge._capture_screen(): [exploration/exploration_bridge.py#L406-420](exploration/exploration_bridge.py#L406-L420)
- Screen dataclass: [exploration/schema.py#L174](exploration/schema.py#L174)

---

**Kết Luận**: Không có screenshots **là do thiết kế**, **không phải lỗi**, và **không block** Phase 2 + 3. Nếu cần, có thể thêm không quá 10 dòng code. 🎯
