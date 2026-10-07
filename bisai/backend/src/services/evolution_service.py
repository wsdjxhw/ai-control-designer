"""
演化引擎编排服务 —— B 层封装 C 成员的 EvolutionEngine

核心职责：
  - 接收路由层的"启动演化"请求
  - 创建 C 的 EvolutionEngine 实例，传给它工作目录和场景配置
  - 在线程池中异步执行（引擎是同步的，不能阻塞 FastAPI 事件循环）
  - 演化结束后更新数据库记录 Project 和 EvolutionRun
  - 将结果（最优参数、演化日志、诊断报告）写入文件存储

为什么用线程池而不是直接 async：
  EvolutionEngine.run() 内部跑的是 CMA-ES（Optuna）+ NumPy/SciPy 仿真，
  这些库是同步的，没有 async 版本。如果在异步协程里直接调用，
  会阻塞整个事件循环，所有 API 请求都会卡住。
  所以用 loop.run_in_executor() 丢到线程池里跑。
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.src.database import SessionLocal
from backend.src.models import EvolutionRun, Project
from backend.src.services.file_storage import FileStorageService

# 全局线程池，最多 2 个演化同时运行
# 为什么要限制：CMA-ES 优化很耗 CPU，同时跑太多会把机器拖垮
# 超过 2 个排队等待，不会丢失请求
_thread_pool = ThreadPoolExecutor(max_workers=2)


class EvolutionService:
    """演化编排服务

    每个演化中的项目对应一个 EvolutionService 实例，
    存在类变量 _instances 缓存中，供路由层通过 project_id 查询状态。
    演化结束后自动从缓存中移除。
    """

    # 运行中实例缓存 {project_id: EvolutionService}
    # 为什么要缓存：前端轮询 get_status 时需要获取运行中的 engine 对象
    # 如果不缓存，每次轮询都得新建一个 EvolutionService，拿不到 engine
    _instances: dict[str, "EvolutionService"] = {}

    def __init__(self, project_id: str, db: Session):
        self.project_id = project_id
        self.db = db
        self.file_storage = FileStorageService()
        self._engine = None  # C 的 EvolutionEngine 实例，演化启动后才创建
        self._run_id: str = ""

    async def start_evolution(
        self,
        max_iterations: int = 20,
        control_law_code: Optional[str] = None,
        start_version_override: Optional[int] = None,
    ) -> str:
        """启动演化

        流程：
          1. 查项目是否存在、是否已在运行
          2. 创建 EvolutionRun 数据库记录（立即写入，状态 running）
          3. 更新 Project.status = running
          4. 创建 C 的 EvolutionEngine 实例
          5. 把自己注册到 _instances 缓存（供前端轮询）
          6. 丢进线程池异步执行（不等待，立即返回 run_id）

        返回 run_id，前端拿到后可以轮询 /evolution/{run_id}/status

        Args:
            max_iterations: 最大演化轮数
            control_law_code: 初始控制律代码（可选，不传则从文件读取最新版本）

        Returns:
            演化运行记录的 run_id（UUID 字符串）
        """
        # C 的 EvolutionEngine
        from core.evolution.engine import EvolutionEngine

        # ---------- 校验 ----------
        project = self.db.query(Project).filter(
            Project.project_id == self.project_id
        ).first()
        if not project:
            raise ValueError("项目不存在")
        if project.status == "running":
            raise ValueError("该项目已有演化在运行中")

        # ---------- 准备参数 ----------
        work_dir = project.work_dir          # data/projects/{id}/
        scene_config = project.scene_config or {}  # 从数据库取场景配置

        # 🆕 详细调试：打印 scene_config 的完整内容
        print(f"[EvolutionService] ========== 开始读取 scene_config ==========")
        print(f"[EvolutionService] DEBUG: project.scene_config type={type(project.scene_config)}")
        print(f"[EvolutionService] DEBUG: scene_config value={project.scene_config}")
        print(f"[EvolutionService] DEBUG: bool(scene_config)={bool(scene_config)}")
        if scene_config:
            print(f"[EvolutionService] DEBUG: model_type={repr(scene_config.get('model_type'))}")
            print(f"[EvolutionService] DEBUG: Has _model_code={bool(scene_config.get('_model_code'))}")
            print(f"[EvolutionService] DEBUG: All keys={list(scene_config.keys())}")

        # 🆕 如果 scene_config 为空或缺少 model_type，尝试从文件加载
        # 注意：只有当数据库中没有 scene_config 时才从文件加载，避免覆盖已有的 _model_code
        if not scene_config or not scene_config.get("model_type"):
            print(f"[EvolutionService] scene_config 为空或缺少 model_type，尝试从文件加载...")
            loaded = self.file_storage.load_scene_config(self.project_id)
            if loaded:
                scene_config = loaded
                print(f"[EvolutionService] 从文件加载成功: model_type={loaded.get('model_type')}")
                print(f"[EvolutionService] 文件加载的 scene_config keys={list(loaded.keys())}")
            else:
                print(f"[EvolutionService] 文件加载也失败，scene_config 仍然为空")
        else:
            print(f"[EvolutionService] 使用数据库中的 scene_config (包含 _model_code={bool(scene_config.get('_model_code'))})")

        # 🆕 最终传递给 EvolutionEngine 的 scene_config
        print(f"[EvolutionService] ========== 最终 scene_config ==========")
        print(f"[EvolutionService] model_type={repr(scene_config.get('model_type', '')) if scene_config else 'None'}")
        print(f"[EvolutionService] Has _model_code={bool(scene_config.get('_model_code')) if scene_config else False}")

        # 🆕 新手模式自动生成 scene_config（如果仍为空）
        if project.mode == "newbie" and (not scene_config or not scene_config.get("model_type")):
            print(f"[EvolutionService] 🔄 检测到新手模式且 scene_config 为空，调用 LLM 自动生成...")
            try:
                from core.llm.newbie import generate_scene
                result = generate_scene(project.description or "通用控制系统")
                scene_config = result.get("scene_config", {})
                model_code = result.get("model_code", "")

                # 将 model_code 注入到 scene_config 中（供 _create_model 动态加载）
                if model_code:
                    scene_config["_model_code"] = model_code
                    print(f"[EvolutionService] ✅ LLM 生成成功: model_type={scene_config.get('model_type')}")
                    print(f"[EvolutionService]    model_code 长度: {len(model_code)} 字符")

                    # 保存到数据库和文件
                    project.scene_config = scene_config
                    self.file_storage.save_scene_config(self.project_id, scene_config)
                    self.file_storage.save_model_code(self.project_id, model_code)
                    self.db.commit()
                    print(f"[EvolutionService] 💾 scene_config 和 model_code 已保存")
                else:
                    print(f"[EvolutionService] ⚠️ LLM 返回的 model_code 为空")
            except Exception as e:
                print(f"[EvolutionService] ❌ 新手模式自动生成失败: {e}")
                import traceback
                traceback.print_exc()
                raise ValueError(f"新手模式自动生成 scene_config 失败: {e}")

        # 🆕 调试日志
        print(f"[EvolutionService] project_id={self.project_id}, scene_config keys={list(scene_config.keys()) if scene_config else []}")
        print(f"[EvolutionService] model_type={repr(scene_config.get('model_type', '')) if scene_config else 'None'}")

        # ---------- 1. 创建演化运行记录 ----------
        # 🆕 从文件系统扫描最新控制律版本，作为起始版本
        # ---------- 1. 创建演化运行记录 ----------
        # 🆕 从文件系统扫描控制律版本
        existing_versions = self.file_storage.list_control_law_versions(self.project_id)
        if start_version_override is not None:
            start_version = start_version_override
            print(f"[EvolutionService] 用户指定从 v{start_version} 开始（已有: {existing_versions}）")
        else:
            start_version = max(existing_versions) if existing_versions else 1
            print(f"[EvolutionService] 从最新版 v{start_version} 开始（已有: {existing_versions}）")

        run = EvolutionRun(
            project_id=self.project_id,
            version=start_version,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        # ---------- 2. 更新项目状态 ----------
        project.status = "running"
        self.db.commit()

        # ---------- 3. 创建引擎 ----------
        engine = EvolutionEngine(
            work_dir=work_dir,
            scene_config=scene_config,
        )
        self._engine = engine
        self._run_id = run.run_id

        # ---------- 4. 注册到缓存（供轮询用）----------
        EvolutionService._instances[self.project_id] = self

        # ---------- 5. 丢进后台线程执行 ----------
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            _thread_pool,
            self._run_evolution_sync,
            engine, run.run_id, max_iterations, control_law_code, start_version,
        )
        return run.run_id

    def _run_evolution_sync(
        self,
        engine,
        run_id: str,
        max_iterations: int,
        control_law_code: Optional[str],
        start_version: int,
    ) -> None:
        """同步执行演化（在线程池中运行）

        这个函数在后台线程中运行，不阻塞 API。
        注意：这里不能用 self.db（SQLAlchemy session 不是线程安全的），
        必须创建独立的数据库会话 SessionLocal()。

        演化结束后做的事：
          - 成功：更新 run + project 状态为 completed，保存参数/日志到文件
          - 失败：更新状态为 failed
          - 异常：捕获所有异常，确保数据库状态更新为 failed，不会卡死在 running
        """
        # 线程隔离的数据库会话
        session = SessionLocal()
        try:
            # ---------- 准备控制律代码 ----------
            code = control_law_code
            if not code:
                # 如果路由层没传代码，从文件系统读最新的
                versions = self.file_storage.list_control_law_versions(self.project_id)
                if versions:
                    latest = versions[-1]
                    code = self.file_storage.load_control_law(self.project_id, latest)

            # ---------- 运行演化 ----------
            # 集成 D 的 LLM 诊断/修改回调（D 已交付 core/llm/）。
            # 签名映射（C 引擎传参 → D 函数参数）：
            #   C: diagnose(metrics_text, layered_history, anomalies)
            #   D: generate_diagnostic_report(metrics_text, history_summary, anomalies)
            #   C: modify(old_code, diagnosis, layered_history)
            #   D: modify_control_law(current_code, diagnosis_report, history_summary)
            # D 的函数内置重试与兜底：即使 LLM 调用失败，
            # 诊断退化为兜底文本、修改返回 None（不改变代码），演化不会崩。
            llm_callbacks = None
            try:
                from core.llm.diagnosis import generate_diagnostic_report
                from core.llm.code_modify import modify_control_law

                llm_callbacks = {
                    "diagnose": lambda m, h, a: generate_diagnostic_report(m, h, a),
                    "modify": lambda c, d, h, sc: modify_control_law(c, d, h, scene_config=sc),
                }
            except ImportError:
                # D 的模块未就绪时退化为无 LLM 的纯 CMA-ES 演化
                llm_callbacks = None

            # 🆕 再次确认起始版本（线程内的数据库会话可能不同步）
            # existing_versions = self.file_storage.list_control_law_versions(self.project_id)
            # start_version = max(existing_versions) if existing_versions else 1

            result = engine.run(
                max_iterations=max_iterations,
                control_law_code=code,
                llm_callbacks=llm_callbacks,
                start_version=start_version,
            )

            # ---------- 查询数据库记录（用独立 session）----------
            run = session.query(EvolutionRun).filter(
                EvolutionRun.run_id == run_id
            ).first()
            project = session.query(Project).filter(
                Project.project_id == self.project_id
            ).first()

            # ---------- 处理演化结果 ----------
            if result["success"]:
                run.status = "completed"
                run.total_cost = result["best_cost"]
                run.best_params = result["best_params"]
                run.completed_at = datetime.now(timezone.utc)

                project.status = "completed"
                project.best_cost = result["best_cost"]
                # 🆕 用文件系统里最大的控制律版本号
                final_versions = self.file_storage.list_control_law_versions(self.project_id)
                project.current_version = max(final_versions) if final_versions else result["final_version"]

                # 保存到文件系统
                self.file_storage.save_best_params(
                    self.project_id, result["final_version"], result["best_params"]
                )
                # 写诊断报告：先读 C 的完整演化日志（此时还没被覆盖），
                # 把每轮真实诊断按版本号落盘 diagnostic_v{N}.txt，
                # 供 /diagnosis 接口查询。
                # （C 的 logger 已在演化过程中把每轮 diagnosis_summary 写入该文件）
                log_records = self.file_storage.load_evolution_log(
                    self.project_id
                ) or []
                for rec in log_records:
                    version = rec.get("version")
                    if not version:
                        continue
                    cost = rec.get("cost")
                    cost_line = f"本轮代价: {cost:.6f}\n" if cost is not None else ""
                    note = ""
                    if version == result["final_version"]:
                        note = f"\n[演化完成] 最优代价: {result['best_cost']:.6f}\n"
                    self.file_storage.save_diagnostic(
                        self.project_id, version,
                        f"===== V{version} 演化诊断报告 =====\n"
                        f"{cost_line}{rec.get('diagnosis', rec.get('diagnosis_summary', ''))}\n{note}",
                    )

                # 🆕 不再覆盖 evolution_log.json！
                # 引擎内部的 EvolutionLogger 已经是「加载已有 + 追加」模式，
                # 之前的代码用 result["history"] 覆盖会把历史轮次冲掉。
                # 这里保留 result["history"] 供调试，但不写文件。
                print(f"[evolution_service] 本次演化轮次: {len(result.get('history', []))}, "
                      f"evolution_log.json 保留（引擎已追加）")
            else:
                # --- 失败 ---
                run.status = "failed"
                run.completed_at = datetime.now(timezone.utc)
                project.status = "failed"

            session.commit()

        except Exception as e:
            # 捕获所有异常，确保状态不会永远 stuck 在 running。
            # 打印异常与堆栈，否则失败原因被吞掉，前端只会看到 status=failed
            # 无法排查（日志输出到 uvicorn 的 stdout/stderr）。
            import traceback
            print(f"[evolution_service] 演化异常: {e}")
            traceback.print_exc()
            try:
                run = session.query(EvolutionRun).filter(
                    EvolutionRun.run_id == run_id
                ).first()
                if run:
                    run.status = "failed"
                    run.completed_at = datetime.now(timezone.utc)
                project = session.query(Project).filter(
                    Project.project_id == self.project_id
                ).first()
                if project:
                    project.status = "failed"
                session.commit()
            except Exception:
                pass  # 如果连异常处理都失败了，就放弃（日志文件已写入的不会丢）
        finally:
            session.close()
            # 从缓存中移除
            EvolutionService._instances.pop(self.project_id, None)
            print(f"[EvolutionService] 演化结束，已从缓存移除 project_id={self.project_id[:8]}...")

    def get_status(self) -> dict:
        """获取当前演化状态

        如果引擎还没创建（比如还没启动过演化），从数据库读项目状态。
        如果引擎在运行中，从 EvolutionEngine.get_status() 获取实时状态。

        返回格式：
          {
              "status": "running",          # idle/running/optimizing/diagnosing/.../completed/failed
              "current_version": 3,
              "best_cost": 0.123,
              "message": "迭代 3/20",
              "is_running": True/False,
          }
        """
        if self._engine is None:
            # 还没启动演化，从数据库读
            project = self.db.query(Project).filter(
                Project.project_id == self.project_id
            ).first()
            return {
                "status": project.status if project else "idle",
                "current_version": project.current_version if project else 0,
                "best_cost": project.best_cost if project else None,
                "message": "",
                "is_running": False,
            }

        # 引擎正在运行/已完成，从引擎拿实时状态
        state = self._engine.get_status()
        return {
            "status": state.status,
            "current_version": state.current_version,
            "best_cost": state.best_cost if state.best_cost != float("inf") else None,
            "message": state.message,
            "is_running": state.is_running,
        }

    @classmethod
    def get_instance(cls, project_id: str, db: Session) -> "EvolutionService":
        """获取或创建演化服务实例

        优先从缓存中取（能拿到正在运行的 engine），
        缓存中没有就建一个新的（用于查询已完成项目的状态）。
        """
        if project_id in cls._instances:
            return cls._instances[project_id]
        return cls(project_id, db)


    def request_stop(self) -> bool:
        """请求中断当前演化（供 B-8 中断接口调用）

        Returns:
            True 表示成功设置了中断标志，False 表示当前没有正在运行的演化
        """
        if self._engine is None:
            return False
        self._engine.request_stop()
        return True

    @classmethod
    def find_by_run_id(cls, run_id: str, db: Session) -> Optional["EvolutionService"]:
        """通过 run_id 找到对应的运行中实例（供中断接口用）

        遍历 _instances 缓存，找到 self._run_id == run_id 的实例。
        """
        for svc in cls._instances.values():
            if svc._run_id == run_id:
                return svc
        return None
