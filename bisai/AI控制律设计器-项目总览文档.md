# 基于AI的物理系统通用控制律自动设计器 —— 项目总览文档

> 生成日期：2026-07-21 | 版本：v1.0（终版）

---

## 一、项目定位与核心创新点

| 维度 | 说明 |
| --- | --- |
| **核心目标** | 构建跨领域（ODE/PDE、连续/开关控制）的通用控制律自动演化平台 |
| **技术闭环** | 建模 → 控制律代码生成 → 参数优化(CMA-ES) → 仿真评估 → LLM诊断 → 结构修改 → 版本进化 |
| **差异化优势** | ① 领域无关的抽象引擎；② 可插拔代价函数（模板/表达式/代码）；③ RAG策略库复用；④ 物理监督员双层验证 |
| **交付形态** | Web应用（FastAPI挂载预编译静态前端）+ start.bat/start.sh 一键启动 |
| **评审适配** | 单Python进程 + SQLite单文件 + 内嵌ChromaDB，零外部依赖，离线可运行 |

---

## 二、最终技术架构（四层）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Layer 4: 表现层 (Presentation)                                             │
│  React 18 + TypeScript + Tailwind CSS + ECharts + Zustand                   │
│  构建产物: npm run build → backend/static/ (预编译提交)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 3: 网关层 (Gateway) ← 【B成员 - 你的职责】                          │
│  FastAPI + Uvicorn + SQLite (文件型数据库)                                   │
│  ├── RESTful API (/api/v1/*)                                                │
│  ├── 静态文件服务 (/static/*) ← 前端JS/CSS                                  │
│  ├── SPA回退 (/* → index.html)                                              │
│  ├── 异步任务 (BackgroundTasks，演化长时间运行)                              │
│  ├── 文件存储 (本地目录 ./data/projects/)                                    │
│  └── LLM Gateway (多模型路由、指数退避重试)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 2: 核心引擎层 (Core Engine)                                           │
│  ├─ Base抽象: Model | Solver | Cost | ControlLaw                            │
│  ├─ 模型: UWSNModel | SIRModel | DCMotorModel                              │
│  ├─ 求解器: PDE_RK4_Solver | ODE_Scipy_Solver                              │
│  ├─ 代价函数: TemplateCost | ExpressionCost | CodeCost                      │
│  ├─ 演化引擎: EvolutionEngine (状态机) | 收敛检测 | 参数边界                │
│  ├─ 控制律: Loader | Validator | SmokeTester                                │
│  └─ 诊断提取: BaseExtractor | UWSN/SIR/Motor 特化                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 1: 智能层 (AI Layer)                                                 │
│  ├─ LLM: Gateway | Prompt模板库 | 诊断 | 修改 | 策略解析                    │
│  ├─ 物理验证: L1 LLM语义 | L2 SymPy | L3 烟雾测试                          │
│  └─ RAG: ChromaDB PersistentClient + 本地Embedding                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 部署与访问方式

| 平台 | 运行方式 | 访问方式 |
| --- | --- | --- |
| **Windows** | 双击 `start.bat` → 启动Python后端 + 打开浏览器 | `http://localhost:8000` |
| **Linux** | `bash start.sh` | `http://localhost:8000` |
| **Android/iOS** | **不安装任何程序** | 连接同WiFi，浏览器访问 `http://{笔记本IP}:8000` |

---

## 三、统一数据流（单次演化迭代 Vn → Vn+1）

```
scene_config.json ──► [C] 工厂创建 Model + Solver + Cost
                           │
control_v{n}.py ────► [C] BaseControlLaw Loader (解析参数名+声明边界)
                           │
                    [C] EvolutionEngine.run()
                           │
                    ┌──────▼──────┐
                    │  OPTIMIZING │◄── [C] CMA-ES (Optuna)
                    │  (参数优化)  │    └── 粗筛20%步数 → 全精度100%
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  SIMULATING │◄── [C] Solver.step() + Cost.integrate()
                    │  (完整仿真)  │    └── 收集 state_history, control_history
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  DIAGNOSING │◄── [D] LLM诊断报告生成
                    │  (LLM诊断)   │    └── metrics + history + physics_prior
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  MODIFYING  │◄── [D] LLM修改控制律
                    │  (代码进化)  │    └── auto_fix + syntax_check + smoke_test
                    └──────┬──────┘
                           │
                    [C] 收敛检测 ──► 未收敛 ──► 保存 Vn+1，继续下一轮
                           │
                           ▼ 收敛/达max_iter
                         DONE
```

---

## 四、完整目录结构（精确到文件）

```
ai-control-designer/
├── start.bat                          # Windows一键启动脚本
├── start.sh                           # Linux/Mac一键启动脚本
├── requirements.txt                   # 根目录统一Python依赖
├── README.md                          # 使用说明（含Python安装指引）
│
├── web/                               # ← A成员：前端源码
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── vite.config.ts                 # build.outDir指向backend/static
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── types/
│       │   └── api.ts
│       ├── stores/
│       │   ├── projectStore.ts
│       │   ├── evolutionStore.ts
│       │   └── settingsStore.ts
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── Sidebar.tsx
│       │   ├── TopNav.tsx
│       │   ├── ProjectCard.tsx
│       │   ├── CreateSceneWizard.tsx
│       │   ├── ExpertEditor.tsx
│       │   ├── ConfigForm.tsx
│       │   ├── CodeEditor.tsx
│       │   ├── EvolutionMonitor.tsx
│       │   ├── ProgressBar.tsx
│       │   ├── CostCurveChart.tsx
│       │   ├── StateTrajectoryChart.tsx
│       │   ├── ControlActivityChart.tsx
│       │   ├── VersionTree.tsx
│       │   ├── DiagnosisReport.tsx
│       │   ├── StrategyParser.tsx
│       │   ├── RagSearchPanel.tsx
│       │   └── SystemSettings.tsx
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── ProjectDetail.tsx
│       │   ├── NewProject.tsx
│       │   ├── EvolutionView.tsx
│       │   ├── StrategyLibrary.tsx
│       │   └── Settings.tsx
│       └── api/
│           └── client.ts
│
├── backend/                           # ← B成员（你）：网关层
│   ├── src/
│   │   ├── main.py                    # FastAPI入口, StaticFiles挂载, SPA回退
│   │   ├── config.py                  # Pydantic Settings
│   │   ├── database.py                # SQLite engine + session
│   │   ├── models/                    # SQLAlchemy ORM
│   │   │   ├── __init__.py
│   │   │   ├── project.py
│   │   │   └── evolution_run.py
│   │   ├── routers/                   # API路由（7个模块）
│   │   │   ├── __init__.py
│   │   │   ├── projects.py            # 项目CRUD
│   │   │   ├── evolution.py           # 演化状态轮询
│   │   │   ├── diagnostics.py         # 诊断报告
│   │   │   ├── rag.py                 # RAG检索/存储
│   │   │   ├── llm.py                 # 新手生成/物理验证
│   │   │   └── system.py              # 系统设置
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── project_service.py
│   │   │   ├── evolution_service.py
│   │   │   ├── file_storage.py
│   │   │   ├── rag_client.py          # ChromaDB内嵌客户端
│   │   │   └── llm_gateway.py
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── project.py
│   │       ├── scene_config.py
│   │       └── system.py
│   └── static/                        # 前端构建产物（npm run build生成）
│       ├── index.html
│       └── assets/
│
├── core/                              # ← C成员：核心引擎
│   ├── __init__.py
│   ├── base/                          # 4个抽象基类
│   │   ├── __init__.py
│   │   ├── base_model.py
│   │   ├── base_solver.py
│   │   ├── base_cost.py
│   │   └── base_control_law.py
│   ├── models/                        # 3个领域模型
│   │   ├── __init__.py
│   │   ├── uwsn_model.py
│   │   ├── sir_model.py
│   │   └── dc_motor_model.py
│   ├── solvers/                       # 2个求解器
│   │   ├── __init__.py
│   │   ├── pde_rk4_solver.py
│   │   └── ode_scipy_solver.py
│   ├── cost_functions/                # 3模式代价函数
│   │   ├── __init__.py
│   │   ├── factory.py
│   │   ├── template_cost.py
│   │   ├── expression_cost.py
│   │   └── code_cost.py
│   ├── control_law/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   └── validator.py
│   ├── evolution/
│   │   ├── __init__.py
│   │   ├── engine.py                  # 演化引擎（状态机驱动）
│   │   ├── logger.py
│   │   ├── state.py
│   │   ├── convergence.py
│   │   ├── param_bounds.py
│   │   └── diagnostics/
│   │       ├── __init__.py
│   │       ├── base_extractor.py
│   │       ├── uwsn_extractor.py
│   │       ├── sir_extractor.py
│   │       └── motor_extractor.py
│   ├── llm/                           # ← D成员：LLM/RAG
│   │   ├── __init__.py
│   │   ├── gateway.py
│   │   ├── diagnosis.py
│   │   ├── code_modify.py
│   │   ├── newbie.py
│   │   ├── strategy_parser.py
│   │   ├── physics_validator.py
│   │   └── prompts/
│   │       ├── vectorization_rules.txt
│   │       ├── uwsn_physics.txt
│   │       ├── sir_physics.txt
│   │       ├── motor_physics.txt
│   │       ├── newbie_guide.txt
│   │       ├── diagnosis_template.txt
│   │       ├── code_modify_template.txt
│   │       └── strategy_parse.txt
│   └── rag/
│       ├── __init__.py
│       ├── client.py
│       ├── embedding.py
│       ├── indexer.py
│       └── retriever.py
│
├── config/
│   ├── __init__.py
│   ├── system_config.py
│   └── scene_schema.py
│
├── scene_configs/                     # 3个案例预设
│   ├── uwsn_scene.json
│   ├── sir_scene.json
│   └── motor_scene.json
│
└── data/                              # 运行时数据（gitignore）
    ├── app.db                         # SQLite数据库
    ├── chroma_db/                     # ChromaDB持久化目录
    ├── system_settings.json
    └── projects/
        └── {project_id}/
            ├── scene_config.json
            ├── model_code.py
            ├── cost_function.py
            ├── control_v1.py
            ├── control_v2.py
            ├── best_params_v1.json
            ├── diagnostic_v1.txt
            └── evolution_log.json
```

---

## 五、四位成员分工与接口契约

### 5.1 职责矩阵

| 成员 | 角色 | 核心交付物 | 技术栈 |
| --- | --- | --- | --- |
| **A** | 前端开发 | 可交互Web前端（6页面 + 15+组件） | React 18 + TS + Tailwind + ECharts + Zustand |
| **B（你）** | 后端/网关 | FastAPI服务（7路由模块）+ SQLite + 启动脚本 | Python + FastAPI + SQLAlchemy + Uvicorn |
| **C** | 核心引擎 | 通用演化引擎 + 3案例模型 + 求解器 + 代价函数 | Python + NumPy + SciPy + Optuna + SymPy |
| **D** | LLM/RAG | LLM全链路 + RAG系统 + 物理验证 + Prompt工程 | Python + LangChain + ChromaDB |

### 5.2 关键接口契约

#### A ↔ B：REST API 契约

```
POST   /api/v1/projects                         # 创建项目
GET    /api/v1/projects                         # 项目列表
GET    /api/v1/projects/{id}                    # 项目详情
POST   /api/v1/projects/{id}/evolution/start    # 启动演化（返回task_id）
GET    /api/v1/evolution/{task_id}/status       # 轮询状态
GET    /api/v1/evolution/{task_id}/versions     # 版本列表
GET    /api/v1/evolution/{task_id}/versions/{v} # 版本详情（含诊断报告）
GET    /api/v1/evolution/{task_id}/compare      # 多版本对比数据
POST   /api/v1/rag/search                       # RAG策略检索
POST   /api/v1/llm/parse-strategy               # 策略自然语言解析
```

#### B ↔ C：Python 函数调用契约

```python
# B调用C的唯一入口
from core.evolution.engine import EvolutionEngine

engine = EvolutionEngine(
    work_dir="/data/projects/{project_id}",
    scene_config=scene_config_dict      # 来自用户上传
)

# 后台任务中执行
result = engine.run(max_iterations=20)
# result = {
#   "success": bool,
#   "final_version": int,
#   "best_cost": float,
#   "best_params": dict,
#   "history": [...],
#   "error": str | None
# }

# 状态轮询
status = engine.get_status()  # EvolutionState对象
```

#### C ↔ D：Python 函数调用契约

```python
# C调用D的3个核心接口

# 1. 诊断报告生成
from core.llm.diagnosis import generate_diagnostic_report
diagnosis = generate_diagnostic_report(
    metrics=metrics_dict,
    history_summary=history_text,
    physics_prior_path="core/llm/prompts/{domain}_physics.txt",
    anomalies=list_of_anomalies
)

# 2. 控制律修改
from core.llm.code_modify import modify_control_law
new_code = modify_control_law(
    current_code=old_code_str,
    diagnosis_report=diagnosis,
    history_summary=history_text,
    vectorization_rules="core/llm/prompts/vectorization_rules.txt"
)

# 3. 物理验证
from core.llm.physics_validator import validate_physics
validation_result = validate_physics(
    model_code=model_code_str,
    scene_config=scene_config_dict,
    level="L1"  # L1/L2/L3
)
```

---

## 六、演化引擎内部状态机

```
IDLE ──(start)──→ INITIALIZING ──(组件就绪)──→ OPTIMIZING
                                                        │
                                    (trial pruned)      │ (best found)
                                    ↓                   ↓
                              [继续采样]          SIMULATING
                                                        │
                                                        ↓
                                                  DIAGNOSING
                                                        │
                              ┌────────────────────────┘
                              │ (未收敛且未达max_iter)
                              ↓
                         MODIFYING ──(code valid)──→ [保存Vn+1] ──→ OPTIMIZING
                              │
                              │ (code invalid x3)
                              ↓
                           FAILED
                              │
        (收敛或达max_iter)    │
    ←─────────────────────────┘
         COMPLETED
```

---

## 七、用户操作流程（双模式）

### 7.1 专家模式

```
[双击start.bat / ./start.sh]
    ↓
[浏览器打开 http://localhost:8000]
    ↓
[创建项目 → 专家模式]
    ↓
[上传 model_code.py] ──→ [物理监督员L1验证]
    ↓                              ↓ (失败)
[编辑 scene_config.json] ←─────────┘
    ↓ (通过)
[上传 control_v1.py] 或 [从RAG检索相似策略]
    ↓
[配置系统设置：LLM/优化器] (可选)
    ↓
[启动演化 → 轮询状态 → 查看诊断报告 → 策略解析 → 存入RAG]
```

### 7.2 新手模式

```
[创建项目 → 新手模式]
    ↓
[自然语言描述系统]
    ↓
[LLM生成草案: scene_config.json + model_code.py + cost_function建议]
    ↓
[可视化确认界面 → 用户修改/确认]
    ↓
[物理验证: L1语义 → L2符号 → L3烟雾测试]
    ↓
[LLM生成初始控制律 → 进入演化流程]
```

---

## 八、现有代码→新架构的映射与重构方案

### 文件映射总表

| 现有文件 | 处理方式 | 新位置 |
| --- | --- | --- |
| `parameter.py` | **淘汰**，数据转入JSON | `scene_configs/uwsn_scene.json` |
| `orchestrator.py` | **重写** | `core/evolution/engine.py` |
| `model.py` | **拆分** | `core/solvers/pde_rk4_solver.py` + `core/models/uwsn_model.py` |
| `llm_utils.py` | **拆分** | `core/llm/gateway.py` + `diagnosis.py` + `code_modify.py` |
| `evolution_logger.py` | **迁移增强** | `core/evolution/logger.py` |
| `diagnostic_extractor.py` | **抽象+扩展** | `core/evolution/diagnostics/base_extractor.py` + `uwsn_extractor.py` |
| `diagnostic_extractor_v2.py` | **抽象+扩展** | 并入 `core/evolution/diagnostics/` |
| `config.py` | **拆分** | `backend/src/config.py` + `core/config.py` |
| `initial_prompt_v1.txt` | **模板化** | `core/llm/prompts/` 下3个文件 |

### 9步重构顺序

| Step | 负责人 | 内容 | 周次 |
| --- | --- | --- | --- |
| Step 1 | C | 搭建4个抽象基类（Model/Solver/Cost/ControlLaw） | W1 |
| Step 2 | C | UWSN案例迁移（模型+RK4求解器+scene_config JSON化） | W1-W2 |
| Step 3 | C | 通用代价函数（TemplateCost + Factory） | W2 |
| Step 4 | C | 重写EvolutionEngine（状态机+通用仿真循环） | W2-W3 |
| Step 5 | D | LLM层拆分与增强（Gateway/Diagnosis/CodeModify/Prompts） | W1-W4 |
| Step 6 | D | RAG系统（ChromaDB + Indexer + Retriever） | W4-W5 |
| Step 7 | **B（你）** | **后端API（7路由模块 + SQLite + 启动脚本）** | W3-W5 |
| Step 8 | A | 前端界面（6页面 + 15+组件） | W3-W6 |
| Step 9 | C | 新增SIR模型和DCMotor模型 | W5-W6 |

---

## 九、8周开发计划（W1-W8）

| 周次 | A（前端） | **B（你 - 后端/网关）** | C（核心引擎） | D（LLM/RAG） |
| --- | --- | --- | --- | --- |
| **W1** | 项目初始化；Vite配置；路由+布局；Monaco编辑器 | **FastAPI骨架；SQLite设计；启动脚本原型** | 4个基类设计；UWSNModel迁移；PDE_RK4_Solver抽象 | LLM Gateway封装（多Key切换）；Prompt模板结构 |
| **W2** | 专家模式UI；ConfigForm；文件上传组件 | **Project CRUD API；文件存储；异步任务框架** | TemplateCost通用化；EvolutionEngine骨架重写 | UWSN物理先验prompt；诊断报告prompt |
| **W3** | 演化监控页；ECharts封装；进度条 | **Evolution API；状态轮询；StaticFiles挂载** | 控制律管理（Loader/Validator/SmokeTest） | 代码修改模块；烟雾测试集成 |
| **W4** | 诊断报告页；版本树UI；策略解析展示 | **RAG API；ChromaDB集成；LLM路由** | 收敛检测；通用指标提取；UWSN诊断适配 | RAG索引器；策略入库；检索+重排 |
| **W5** | RAG搜索面板；策略库UI；系统设置页 | **系统设置API；LLM配置动态切换；集成测试** | SIRModel实现；ODE_Scipy_Solver | SIR物理先验；SIR诊断提取器 |
| **W6** | 新手模式向导UI；物理验证结果展示 | **新手模式API；物理验证API；最终集成** | DCMotorModel实现；三案例端到端 | 电机物理先验；策略解析模块 |
| **W7** | 三案例展示页；响应式适配；UI polish | **性能优化；并发控制；日志管理；脚本最终版** | 三案例对比测试；引擎调优 | RAG检索优化；Prompt调优 |
| **W8** | 演示视频录制；Bug修复；申报书截图 | **最终集成测试；部署文档；数据备份脚本** | 申报书技术章；代码注释 | 申报书AI章；演示案例解说词 |

---

## 十、B成员（你）—— 后端/网关详细职责

### 10.1 核心交付物

| 交付物 | 说明 |
| --- | --- |
| FastAPI服务骨架 | 端口8000，同时提供API + 前端静态文件服务 |
| 7个路由模块 | projects / evolution / diagnostics / rag / llm / system |
| SQLite数据库 | 2个ORM模型（Project / EvolutionRun） |
| 内嵌ChromaDB客户端 | PersistentClient，无需额外服务 |
| 启动脚本 | start.bat（Windows）+ start.sh（Linux/Mac） |
| 文件存储服务 | 本地目录 `./data/projects/` 管理 |
| LLM Gateway服务 | 多模型路由、指数退避重试、流式SSE |

### 10.2 技术栈

- FastAPI + Uvicorn
- SQLAlchemy 2.0 + SQLite
- ChromaDB（PersistentClient内嵌）
- Pydantic v2 + Pydantic-Settings
- aiofiles（文件操作）

### 10.3 关键配置文件

**backend/src/main.py** — FastAPI入口（要点）：
- API路由先注册，避免被静态文件拦截
- 挂载 `/static/` 目录提供前端JS/CSS
- SPA回退：所有非API路由 → `index.html`
- 启动事件：初始化 `data/projects/` 和 `data/chroma_db/` 目录

**backend/src/config.py** — 配置（要点）：
- SQLite: `sqlite:///./data/app.db`
- ChromaDB路径: `./data/chroma_db`
- 项目文件根目录: `./data/projects`
- 默认LLM: ModelScope上的Kimi/K2.5（用户可在设置页修改）

**backend/src/database.py** — 数据库（要点）：
- `check_same_thread=False`（SQLite多线程访问）
- `init_db()` 启动时调用创建表

**backend/src/services/rag_client.py** — ChromaDB（要点）：
- `chromadb.PersistentClient` 内嵌模式
- 同级目录 `data/chroma_db/` 持久化存储
- 全局单例 `rag_client`

### 10.4 启动脚本

**start.bat / start.sh** 一键启动逻辑：
1. 检查Python是否安装
2. 检查 `backend/static/index.html`（前端已构建？未构建则尝试 npm run build）
3. pip install -r requirements.txt
4. 初始化 data/projects/ 和 data/chroma_db/ 目录
5. 启动 uvicorn（`python -m uvicorn src.main:app --host 0.0.0.0 --port 8000`）

### 10.5 B ↔ A 的REST API详细契约

```
# 项目
POST   /api/v1/projects                       # 创建项目
GET    /api/v1/projects                       # 项目列表
GET    /api/v1/projects/{id}                  # 项目详情
PUT    /api/v1/projects/{id}                  # 更新项目
DELETE /api/v1/projects/{id}                  # 删除项目

# 演化
POST   /api/v1/projects/{id}/evolution/start  # 启动演化（BackgroundTasks）
GET    /api/v1/evolution/{task_id}/status     # 轮询状态
GET    /api/v1/evolution/{task_id}/versions   # 版本列表
GET    /api/v1/evolution/{task_id}/versions/{v} # 版本详情
GET    /api/v1/evolution/{task_id}/compare    # 多版本对比

# 诊断
GET    /api/v1/evolution/{task_id}/versions/{v}/diagnosis

# RAG
POST   /api/v1/rag/search                    # 策略检索
POST   /api/v1/rag/store                     # 策略入库（自动，由演化流程触发）

# LLM
POST   /api/v1/llm/generate-scene            # 新手：NL→scene_config
POST   /api/v1/llm/validate-physics          # 物理验证
POST   /api/v1/llm/parse-strategy            # 策略解析

# 系统
GET    /api/v1/system/settings               # 获取系统设置
PUT    /api/v1/system/settings               # 更新系统设置
GET    /api/v1/system/llm-models             # 获取可用LLM模型列表
```

---

## 十一、评审环境适配检查表

| 检查项 | 状态 | 说明 |
| --- | --- | --- |
| 评审机无Docker | ✅ 已解决 | 完全不用Docker |
| 评审机无PostgreSQL | ✅ 已解决 | 改用SQLite单文件 |
| 评审机无Node.js | ✅ 已解决 | 前端预编译提交，无需npm |
| 评审机无ChromaDB服务 | ✅ 已解决 | PersistentClient内嵌 |
| 单端口访问 | ✅ 已解决 | FastAPI 8000端口同时提供API+前端 |
| 离线运行 | ✅ 已解决 | 所有依赖pip安装，除LLM API调用外无网络需求 |
| Windows兼容 | ✅ 已解决 | start.bat |
| Linux/Mac兼容 | ✅ 已解决 | start.sh |

---

## 十二、关键风险与预案

| 风险 | 严重程度 | 预案 |
| --- | --- | --- |
| **LLM API限流/被封** | 🔴 高 | 多模型自动切换（ModelScope→DeepSeek→OpenRouter备用）；每Key独立rate limit；预计算5轮数据作演示保险丝 |
| **CMA-ES现场耗时过长** | 🔴 高 | 现场只跑1-2轮展示闭环；预计算20轮数据回放；多保真度粗筛必须保留 |
| **NumPy/SciPy编译失败** | 🟡 中 | requirements.txt锁定稳定版本；启动脚本捕获ImportError提示VC++ Redist；准备纯Python回退求解器 |
| **100M压缩包限制** | 🟡 中 | 不打包Python依赖和node_modules；只存代价曲线+最终状态+控制律代码；演示视频压缩至480p |
| **移动端访问** | 🟡 中 | 申明B/S架构浏览器访问；确保笔记本和手机同WiFi；关闭防火墙或开放8000端口 |

---

## 十三、W1 立即可执行清单（Day 1-3）

### B成员（你）— W1任务

| 任务 | 验收标准 |
| --- | --- |
| ① FastAPI骨架搭建 | `uvicorn src.main:app` 跑通 |
| ② Health端点 | `/api/health` 返回 `{"status":"ok"}` |
| ③ SQLite数据库设计 | 创建Project和EvolutionRun两个ORM模型 |
| ④ start.bat原型 | 双击能启动服务 |
| ⑤ start.sh原型 | bash能启动服务 |
| ⑥ 静态文件挂载 | `/static/` 目录挂载成功 |

### 其他成员W1任务（供参考）

| 成员 | 任务 | 验收标准 |
| --- | --- | --- |
| A | npm run dev跑通；Create Project调通B的接口 | 前端能创建项目，SQLite出现新记录 |
| C | 创建core/base/ 4个基类；UWSNModel.rhs()输出shape为(M+1,10) | test_rhs.py通过 |
| D | core/llm/目录；gateway.py能正常调用LLM | `python -c "from core.llm.gateway import get_llm; print(get_llm())"` 不报错 |

---

## 十四、交付物清单（比赛提交）

```
ai-control-designer.zip
├── start.bat                    # Windows评审：双击运行
├── start.sh                     # Linux/Mac评审：chmod +x后运行
├── requirements.txt             # 所有Python依赖
├── README.md                    # 使用说明（含Python安装指引、截图）
│
├── web/                         # 前端源码（证明原创性）
│   └── src/
│
├── backend/                     # 后端源码 + 预编译前端
│   ├── src/
│   └── static/                  # npm run build产物（已包含，评审无需装Node）
│       ├── index.html
│       └── assets/
│
├── core/                        # 核心引擎源码
│
├── config/                      # 配置Schema
│
└── data/                        # 运行时数据（可预置演示案例）
    ├── app.db                   # SQLite数据库（预置项目记录）
    ├── chroma_db/               # ChromaDB向量库（预置索引）
    ├── system_settings.json     # 默认系统配置
    └── projects/                # 预置1-2个演示案例
        ├── demo_uwsn/
        └── demo_sir/
```

---

> **注**：此文档综合了项目框架文档和分工实施方案的全部关键内容，B成员（你）的重点职责在"第四节"（目录结构）、"第十节"（后端详细职责）、"第十三节"（W1任务）中已突出标注。整体进度按8周计划推进，每周五按接口契约联调。
