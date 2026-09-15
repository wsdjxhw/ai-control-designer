"""
API 路由模块

各路由注册在 main.py 的 FastAPI 应用上：
  app.include_router(xxx.router, prefix="/api/v1")

当前状态：
  - system.py     : ✅ 已完成（纯 B 层，零依赖）
  - projects.py   : ✅ CRUD已完成（start_evolution 待C接口）
  - rag.py        : ⏳ 骨架（直接调 D 的 core.rag.client，待D交付后补全）
  - llm.py        : ⏳ 骨架（直接调 D 的 core.llm.*，待D交付后补全）
  - evolution.py  : ⏳ 骨架（直接调 C 的 core.evolution.engine，待C接口）
  - diagnostics.py: ⏳ 骨架（待确认诊断获取方式）
"""
