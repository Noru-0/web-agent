# Web Agent System - Hướng Dẫn Nhanh

Tài liệu tổng hợp tất cả lệnh và cấu hình cần thiết để chạy hệ thống web-agent.

---

## 📋 Mục Lục

1. [Cấu Hình Ban Đầu](#cấu-hình-ban-đầu)
2. [Xác Minh Hệ Thống](#xác-minh-hệ-thống)
3. [Khám Phá Website (Exploration)](#khám-phá-website-exploration)
4. [Xử Lý Dữ Liệu](#xử-lý-dữ-liệu)
5. [Huấn Luyện Model](#huấn-luyện-model)
6. [Chạy Agent](#chạy-agent)
7. [Debugging & Testing](#debugging--testing)
8. [Workflow Thông Thường](#workflow-thông-thường)

---

## Cấu Hình Ban Đầu

### 1. Cài Đặt Dependencies

```bash
# Tạo virtual environment
python -m venv .venv

# Kích hoạt venv (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Kích hoạt venv (Windows CMD)
.venv\Scripts\activate.bat

# Cài đặt packages
pip install -r requirements.txt

# Cài đặt Playwright browsers (nếu cần)
playwright install chromium
```

### 2. Cấu Hình File .env

Copy file mẫu và chỉnh sửa:
```bash
copy .env.example .env
```

**Các cấu hình quan trọng:**

```ini
# ===============================
# LLM / Explorer Configuration
# ===============================
# Chọn 1 trong các API keys sau:

# Nếu dùng OpenAI (GPT-4, GPT-3.5)
OPENAI_API_KEY=sk-your-openai-key-here

# Nếu dùng HuggingFace LLaMA (AgentTrek)
HUGGINGFACE_API_KEY=hf_your-huggingface-token-here

# Chọn explorer provider
EXPLORER_PROVIDER=agenttrek           # hoặc: simple
EXPLORER_MODEL=meta-llama/Llama-3.1-8B-Instruct
EXPLORER_BASE_URL=https://api-inference.huggingface.co/v1
EXPLORER_API_KEY=${HUGGINGFACE_API_KEY}
EXPLORER_TEMPERATURE=0.2
EXPLORER_MAX_STEPS=50

# ===============================
# Browser Configuration
# ===============================
BROWSER_HEADLESS=true                  # false để xem browser
BROWSER_TIMEOUT_MS=30000
BROWSER_VIEWPORT_WIDTH=1280
BROWSER_VIEWPORT_HEIGHT=800

# ===============================
# Training Configuration
# ===============================
SLM_DEVICE=cpu                         # hoặc: cuda, mps
SLM_DTYPE=float32
SLM_MAX_SEQ_LEN=2048

# ===============================
# Paths
# ===============================
DATA_DIR=data
RAW_DATA_DIR=data/raw
TRAJECTORY_DIR=data/trajectories
CHECKPOINT_DIR=checkpoints
```

### 3. Lấy API Keys

**HuggingFace Token (cho AgentTrek/LLaMA):**
1. Đăng ký tài khoản tại https://huggingface.co
2. Vào Settings → Access Tokens
3. Tạo token mới với quyền "Read"
4. Copy vào `HUGGINGFACE_API_KEY`

**OpenAI API Key (tùy chọn):**
1. Đăng ký tại https://platform.openai.com
2. Vào API Keys
3. Tạo key mới
4. Copy vào `OPENAI_API_KEY`

---

## Xác Minh Hệ Thống

### Kiểm Tra Toàn Bộ Hệ Thống

```bash
python scripts/verify_system.py
```

**Kiểm tra:**
- ✓ Cấu trúc thư mục
- ✓ Dependencies (Python, PyTorch, Playwright, etc.)
- ✓ File .env và cấu hình
- ✓ Schema module
- ✓ Agent classes
- ✓ Training pipeline
- ✓ Adapter registry
- ✓ Architectural boundaries

**Kết quả mong đợi:** `10/10 checks passed` hoặc `9/10` (some optional deps)

### Kiểm Tra Exploration Pipeline

```bash
python workflows/verify_explore.py
```

**Kiểm tra:**
- ✓ Imports
- ✓ Data models (Screen, Transition, ActionSemantic)
- ✓ Deduplication
- ✓ Storage
- ✓ Text extraction
- ✓ AgentTrek adapter

**Kết quả mong đợi:** `6/6 tests passed`

### Kiểm Tra SLM Agent

```bash
python verify_slm.py
```

**Kiểm tra:**
- ✓ Environment setup
- ✓ Agent instantiation
- ✓ Episode execution
- ✓ Trajectory recording

---

## Khám Phá Website (Exploration)

### 1. Exploration Cơ Bản

```bash
# Chạy với adapter tự động từ .env
python run_exploration.py

# Với URL cụ thể
python run_exploration.py --url https://example.com

# Giới hạn số screens
python run_exploration.py --max-screens 5

# Không headless (xem browser)
python run_exploration.py --no-headless
```

### 2. Exploration với AgentTrek

Đảm bảo cấu hình trong `.env`:
```ini
EXPLORER_PROVIDER=agenttrek
EXPLORER_MODEL=meta-llama/Llama-3.1-8B-Instruct
HUGGINGFACE_API_KEY=hf_your_token_here
```

Chạy exploration:
```bash
python run_exploration.py --url https://example.com --max-screens 50
```

### 3. Output

Kết quả lưu trong:
```
data/raw/{url_folder}/              # Mỗi website 1 thư mục riêng
├── screens.jsonl                   # JSONL: 1 screen/line
├── actions.jsonl                   # JSONL: 1 action/line
├── transitions.jsonl               # JSONL: 1 transition/line
└── metadata.json                   # JSON: metadata
```

**Lưu ý**: Task synthesis (Phase 3) tự động chạy sau exploration!

---

## 📁 Storage System

### URL-Based Folders

**Mỗi website tạo thư mục riêng** dựa trên URL:

| URL | Folder Name |
|-----|-------------|
| `http://localhost:9999` | `localhost_9999` |
| `https://shop.example.com` | `shop.example.com` |
| `https://www.example.com/path` | `example.com` (bỏ www.) |
| `http://192.168.1.1:8080` | `192.168.1.1_8080` |

### Structure

```
data/
├── raw/                            # Exploration results
│   ├── localhost_9999/             # Website 1
│   │   ├── screens.jsonl
│   │   ├── actions.jsonl
│   │   ├── transitions.jsonl
│   │   └── metadata.json
│   ├── shop.example.com/           # Website 2
│   │   └── ...
│   └── example.com_3000/           # Website 3
│       └── ...
└── tasks/                          # Task synthesis results
    ├── localhost_9999/
    │   ├── tasks.json
    │   └── tasks_summary.txt
    └── shop.example.com/
        └── ...
```

### Key Features

✅ **Mỗi website có folder riêng** - Không ghi đè lẫn nhau  
✅ **Không auto-cleanup** - Data cũ được giữ lại  
✅ **Parallel exploration** - Có thể explore nhiều sites cùng lúc  
✅ **Easy management** - Nhìn folder biết ngay website nào  

### Examples

```bash
# Explore nhiều websites - tất cả được giữ lại
python run_exploration.py --url http://localhost:9999
# → data/raw/localhost_9999/

python run_exploration.py --url https://shop.example.com
# → data/raw/shop.example.com/

# Chạy lại cùng website
python run_exploration.py --url http://localhost:9999
# → APPEND vào data/raw/localhost_9999/ (không xóa data cũ)
```

---

## Xử Lý Dữ Liệu

### 1. Convert Explorer Logs

Nếu có raw logs từ external explorer (WebTactiX, AgentTrek):

```bash
# Convert từ WebTactiX format
python scripts/convert_data.py \
    --adapter webtactix \
    --input data/raw/webtactix/trace.json \
    --output data/trajectories/offline/

# Convert từ AgentTrek format
python scripts/convert_data.py \
    --adapter agenttrek \
    --input data/raw/agenttrek/episode.json \
    --output data/trajectories/offline/

# Convert toàn bộ thư mục
python scripts/convert_explorer_output.py \
    --explorer webtactix \
    --input-dir data/raw/webtactix/ \
    --output-dir data/trajectories/offline/
```

### 2. Clean Data

```bash
# Clean và validate trajectories
python scripts/clean_data.py \
    --input data/trajectories/offline/ \
    --output data/cleaned/

# Với filtering
python scripts/clean_data.py \
    --input data/trajectories/offline/ \
    --output data/cleaned/ \
    --min-steps 5 \
    --max-steps 100
```

### 3. Xem Thống Kê Data

```bash
# List adapters
python -c "from adapters.registry import print_available_adapters; print_available_adapters()"

# Check trajectory count
python -c "from pathlib import Path; print(f'Trajectories: {len(list(Path(\"data/trajectories\").rglob(\"*.json\")))}')"
```

---

## Huấn Luyện Model

### 1. Training Cơ Bản

```bash
# Training với cấu hình mặc định
python training/train.py \
    --data-dir data/cleaned/ \
    --checkpoint-dir checkpoints/ \
    --epochs 10 \
    --batch-size 8

# Training với GPU
python training/train.py \
    --data-dir data/cleaned/ \
    --checkpoint-dir checkpoints/ \
    --device cuda \
    --epochs 20 \
    --batch-size 16

# Resume training
python training/train.py \
    --data-dir data/cleaned/ \
    --checkpoint-dir checkpoints/ \
    --resume checkpoints/model_epoch_5.pt
```

### 2. Training với Config File

Tạo `config/training.yaml`:
```yaml
data:
  train_dir: data/cleaned/train
  val_dir: data/cleaned/val
  batch_size: 8
  
model:
  hidden_size: 256
  num_layers: 4
  dropout: 0.1
  
training:
  epochs: 10
  learning_rate: 0.001
  device: cpu
  checkpoint_dir: checkpoints/
```

Chạy:
```bash
python training/train.py --config config/training.yaml
```

### 3. Evaluation

```bash
# Evaluate model
python training/evaluate.py \
    --checkpoint checkpoints/best_model.pt \
    --data-dir data/cleaned/test/ \
    --device cpu

# Với detailed output
python training/evaluate.py \
    --checkpoint checkpoints/best_model.pt \
    --data-dir data/cleaned/test/ \
    --output results/eval_results.json \
    --verbose
```

---

## Chạy Agent

### 1. Simple Agent (Không Cần Training)

```bash
# Chạy rule-based agent
python examples/run_agent.py

# Với options
python examples/run_agent.py --headless --steps 10

# Agent loại khác
python examples/run_agent.py --agent click_first
python examples/run_agent.py --agent random
```

### 2. SLM Agent (Đã Train)

```bash
# Chạy trained agent
python examples/run_slm_agent.py \
    --checkpoint checkpoints/best_model.pt \
    --verbose

# Với GPU
python examples/run_slm_agent.py \
    --checkpoint checkpoints/best_model.pt \
    --device cuda

# Không headless (xem browser)
python examples/run_slm_agent.py \
    --checkpoint checkpoints/best_model.pt \
    --no-headless

# Giới hạn steps
python examples/run_slm_agent.py \
    --checkpoint checkpoints/best_model.pt \
    --max-steps 20
```

### 3. Agent với Recording

```bash
# Chạy và record trajectory
python examples/run_agent_with_recording.py \
    --agent simple \
    --output data/trajectories/online/episode_001.json

# Chạy SLM agent với recording
python examples/run_slm_agent.py \
    --checkpoint checkpoints/best_model.pt \
    --record data/trajectories/online/slm_episode.json \
    --verbose
```

### 4. Batch Execution

```bash
# Chạy nhiều episodes
for i in {1..10}; do
    python examples/run_agent.py --output "results/episode_$i.json"
done
```

---

## Debugging & Testing

### 1. Test Environment

```bash
# Test browser environment
python workflows/test_env.py

# Test specific environment
python -c "
from envs.demo_site.env import DemoEnv
import asyncio

async def test():
    env = DemoEnv()
    obs = await env.reset()
    print(f'URL: {obs[\"url\"]}')
    await env.close()

asyncio.run(test())
"
```

### 2. Test Adapters

```bash
# Test offline adapter
python -c "
from adapters.registry import create_adapter
adapter = create_adapter('webtactix')
print(f'Adapter: {adapter.name}')
"

# Test exploration adapter
python -c "
from exploration.exploration_bridge import get_exploration_adapter
adapter = get_exploration_adapter('agenttrek')
print(f'Explorer: {adapter.explorer_name}')
print(f'Model: {adapter.model_name}')
"
```

### 3. Interactive Python

```bash
# Start Python REPL với imports
python

>>> from agents.simple_agent import SimpleAgent
>>> from agents.slm_agent import SLMAgent
>>> from envs.demo_site.env import DemoEnv
>>> from schema import Action, ActionType
>>> 
>>> # Test something
>>> agent = SimpleAgent()
>>> print(agent)
```

### 4. Debugging với Verbose

Thêm logging vào bất kỳ lệnh nào:
```bash
# Set log level
export LOG_LEVEL=DEBUG  # hoặc trong .env

# Hoặc trong Python
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)

# Your code here
"
```

---

## Workflow Thông Thường

### Workflow 1: Offline Training (Từ Explorer Logs)

```bash
# 1. Chạy external explorer (hoặc có sẵn logs)
python scripts/run_explorer.py --explorer webtactix --task booking

# 2. Convert logs sang unified format
python scripts/convert_data.py \
    --adapter webtactix \
    --input data/raw/webtactix/ \
    --output data/trajectories/offline/

# 3. Clean data
python scripts/clean_data.py \
    --input data/trajectories/offline/ \
    --output data/cleaned/

# 4. Train model
python training/train.py \
    --data-dir data/cleaned/ \
    --checkpoint-dir checkpoints/ \
    --epochs 10

# 5. Evaluate
python training/evaluate.py \
    --checkpoint checkpoints/best_model.pt \
    --data-dir data/cleaned/test/

# 6. Run trained agent
python examples/run_slm_agent.py \
    --checkpoint checkpoints/best_model.pt
```

### Workflow 2: Online Exploration + Training

```bash
# 1. Chạy exploration để thu thập data
python run_exploration.py \
    --url https://example.com \
    --max-screens 100

# 2. Convert exploration results (nếu cần)
# (exploration results đã ở unified format)

# 3. Train trực tiếp
python training/train.py \
    --data-dir data/exploration/agenttrek/ \
    --checkpoint-dir checkpoints/

# 4. Run agent
python examples/run_slm_agent.py \
    --checkpoint checkpoints/best_model.pt
```

### Workflow 3: Quick Testing

```bash
# 1. Verify hệ thống
python scripts/verify_system.py

# 2. Test simple agent (không cần training)
python examples/run_agent.py --headless --steps 5

# 3. Test exploration
python workflows/verify_explore.py

# 4. Done!
```

---

## Cấu Hình Nâng Cao

### Browser Settings

```ini
# Xem browser hoạt động
BROWSER_HEADLESS=false

# Tăng timeout cho trang load chậm
BROWSER_TIMEOUT_MS=60000

# Viewport size khác
BROWSER_VIEWPORT_WIDTH=1920
BROWSER_VIEWPORT_HEIGHT=1080
```

### Explorer Settings

```ini
# Dùng model mạnh hơn
EXPLORER_MODEL=meta-llama/Llama-3.1-70B-Instruct

# Tăng temperature cho diverse actions
EXPLORER_TEMPERATURE=0.7

# Exploration sâu hơn
EXPLORER_MAX_STEPS=100
```

### Training Settings

```ini
# Dùng GPU
SLM_DEVICE=cuda

# Mixed precision training
SLM_DTYPE=float16

# Longer sequences
SLM_MAX_SEQ_LEN=4096
```

---

## Troubleshooting

### Lỗi Thường Gặp

**1. Missing API Key**
```
ERROR: Required environment variable 'HUGGINGFACE_API_KEY' not found
```
→ Thêm API key vào `.env`

**2. Playwright Not Installed**
```
ERROR: Playwright browser not found
```
→ Chạy: `playwright install chromium`

**3. PyTorch Not Found**
```
ImportError: No module named 'torch'
```
→ Cài đặt: `pip install torch`

**4. CUDA Not Available**
```
WARNING: CUDA not available, using CPU
```
→ Cài đặt CUDA-enabled PyTorch: https://pytorch.org/get-started/locally/

**5. Rate Limit (HuggingFace)**
```
ERROR: Rate limit exceeded
```
→ Giảm `EXPLORER_MAX_STEPS` hoặc upgrade HuggingFace Pro

### Kiểm Tra Cấu Hình

```bash
# Check Python version
python --version  # Should be 3.10+

# Check packages
pip list | grep -E "torch|playwright|openai"

# Check .env loaded
python -c "from utils.env import env; print(env.get('EXPLORER_MODEL'))"

# Check adapters
python -c "from adapters.registry import list_adapters; print(list_adapters())"
```

---

## Tài Liệu Bổ Sung

- **[README.md](README.md)** - Overview và architecture
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Chi tiết kiến trúc hệ thống
- **[AGENTTREK_INTEGRATION.md](docs/AGENTTREK_INTEGRATION.md)** - Hướng dẫn AgentTrek
- **[TRAINING.md](training/TRAINING.md)** - Chi tiết training pipeline
- **[ADAPTERS.md](docs/ADAPTERS.md)** - Hướng dẫn tạo adapter mới

---

## Liên Hệ & Đóng Góp

Nếu gặp vấn đề hoặc có câu hỏi:
1. Chạy `python scripts/verify_system.py` để kiểm tra
2. Xem troubleshooting section ở trên
3. Kiểm tra các file docs trong `docs/`

**Happy coding! 🚀**
