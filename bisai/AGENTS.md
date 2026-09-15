# Codex 项目配置

> ⚠️ **本项目继承全局环境配置**，详见 `C:\Users\26966\.Codex\AGENTS.md`

## 环境要求（重要！）

**本项目必须在指定的 Conda 虚拟环境中运行。**

### 环境信息

- **环境名称**: `mcp`
- **Python 路径**: `D:\anaconda\envs\mcp\python.exe`
- **Python 版本**: `3.10.19`
- **创建方式**: Anaconda (conda)

### 激活方式

#### 方式 1：使用完整 Python 路径（推荐，适用于 Codex Bash 工具）

```bash
"D:\anaconda\envs\mcp\python.exe" your_script.py
"D:\anaconda\envs\mcp\python.exe" -m pip install package_name
"D:\anaconda\envs\mcp\python.exe" -m uvicorn backend.src.main:app --reload
```

#### 方式 2：使用 conda run（适用于脚本）

```bash
conda run -n mcp python your_script.py
conda run -n mcp pip install package_name
```

#### 方式 3：手动激活（适用于 VSCode 终端）

```bash
conda activate mcp
python your_script.py
```

### 为什么需要指定环境？

Codex 的 Bash 工具每次调用都是**全新 shell 会话**，不会自动继承当前终端的 conda 环境状态。因此：

- ❌ 不能依赖 `conda activate mcp` 后直接调用 `python`
- ✅ 必须使用完整路径 `D:\anaconda\envs\mcp\python.exe` 或 `conda run -n mcp`

---

## 项目启动

### 一键启动（推荐）

双击运行项目根目录下的启动脚本：

- **Windows**: `start.bat`
- **Linux/Mac**: `start.sh`

启动脚本已配置使用 `mcp` 环境，访问 `http://localhost:8000`。

### 手动启动

```bash
cd "c:\Users\26966\Desktop\源代码\源代码"
"D:\anaconda\envs\mcp\python.exe" -m uvicorn backend.src.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 依赖管理

### 安装依赖

```bash
"D:\anaconda\envs\mcp\python.exe" -m pip install -r requirements.txt
```

### 验证环境

```bash
"D:\anaconda\envs\mcp\python.exe" --version
# 应输出: Python 3.10.19
```

---

## 重要依赖版本锁定

项目 `requirements.txt` 中有严格的版本要求，特别是：

```txt
chromadb==0.5.3
httpx==0.27.2
```

**原因**：`chromadb>=1.0` 与 `openai 1.35.0` 不兼容（`httpx` 版本冲突），会导致 `ModuleNotFoundError: ollama_embedding_function`。

---

## 数据存储位置

- 项目数据: `data/projects/<project_id>/`
- 向量数据库: `data/chroma_db/`
- SQLite 数据库: 由 `backend/src/config.py` 配置

---

## 故障排除

### 问题：`ModuleNotFoundError: chromadb.utils.embedding_functions.ollama_embedding_function`

**原因**：ChromaDB 版本不匹配

**解决**：
```bash
"D:\anaconda\envs\mcp\python.exe" -m pip uninstall chromadb -y
"D:\anaconda\envs\mcp\python.exe" -m pip install chromadb==0.5.3 httpx==0.27.2
```

### 问题：Codex 无法找到 `mcp` 环境

**解决**：所有 Python 命令必须使用完整路径：
```bash
"D:\anaconda\envs\mcp\python.exe" ...
```

---

## 项目架构速览

- **后端**: FastAPI + SQLite + ChromaDB
- **核心引擎**: 演化优化 (CMA-ES) + LLM (OpenAI) + RAG
- **前端**: React 18 (预编译，位于 `backend/static/`)
- **目标**: AI 驱动的物理系统控制律自动设计

更多详情见项目文档和代码注释。
