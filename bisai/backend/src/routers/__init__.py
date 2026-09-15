"""
API 路由模块

各路由注册在 main.py 的 FastAPI 应用上：
  app.include_router(xxx.router, prefix="/api/v1")

当前状态（全部完成，已与 C/D 模块联调通过）：
  - system.py     : ✅ 已完成（纯 B 层，读写 system_settings.json）
  - projects.py   : ✅ 已完成（CRUD + start_evolution 异步启动演化）
  - rag.py        : ✅ 已完成（直接调 D 的 core.rag 快捷函数）
  - llm.py        : ✅ 已完成（直接调 D 的 core.llm.* 业务函数）
  - evolution.py  : ✅ 已完成（状态轮询 / 版本列表 / 版本详情 / 对比，接 C 的 EvolutionEngine）
  - diagnostics.py: ✅ 已完成（按版本读取 diagnostic_v{N}.txt）
"""
