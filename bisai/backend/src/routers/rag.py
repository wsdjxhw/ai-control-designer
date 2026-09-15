"""
RAG 策略库 API 路由

终版实现：B 不封装任何 RAG 逻辑。
B 在 router 中直接调用 D 的 core.rag 快捷函数，只做 HTTP 请求/响应转换。
D 负责 core/rag/ 全部逻辑（ChromaDB 持久化、向量检索）。

调用关系（D 已交付，接口已确认）：
  - /rag/search → core.rag.search_strategies(query, top_k, domain_filter)
  - /rag/store  → core.rag.store_strategy(id, code, domain, version, cost, params, diagnosis_summary)
  - /rag/list   → core.rag.list_strategies(limit)
  - /rag/delete → core.rag.delete_strategy(id)

注意：导入时用别名（rag_search / rag_store / rag_list / rag_delete），
     避免端点函数名与导入的函数名重名导致遮蔽。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# D 的 core.rag 快捷函数（D 已交付）
from core.rag import search_strategies as rag_search
from core.rag import store_strategy as rag_store
from core.rag import list_strategies as rag_list
from core.rag import delete_strategy as rag_delete

router = APIRouter(tags=["rag"])


class SearchRequest(BaseModel):
    query: str = Field(..., description="查询文本")
    top_k: int = Field(5, ge=1, le=20)
    filters: dict | None = Field(None, description="过滤条件（当前支持 domain）")


class StoreRequest(BaseModel):
    id: str = Field(..., description="策略ID，如 uwsn_v12")
    code: str = Field(..., description="控制律代码全文")
    metadata: dict = Field(
        default_factory=dict,
        description="元数据：domain/version/cost/params/diagnosis_summary",
    )


class DeleteRequest(BaseModel):
    id: str = Field(..., description="要删除的策略ID")


@router.post("/rag/search")
async def search_strategies(req: SearchRequest):
    """
    检索相似控制策略（语义检索）

    D 的 search_strategies 内部：
      1. 用 ChromaDB 默认 embedding 把 query 向量化
      2. 在 collection 中按余弦相似度取 top_k
      3. 返回 [{id, code, metadata, similarity}]
    """
    try:
        domain_filter = req.filters.get("domain") if req.filters else None
        results = rag_search(
            query=req.query,
            top_k=req.top_k,
            domain_filter=domain_filter,
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@router.post("/rag/store")
async def store_strategy(req: StoreRequest):
    """
    存储控制策略到 RAG 策略库

    把前端传来的扁平元数据拆成 D 的 store_strategy 需要的具名参数：
      domain / version / cost / params / diagnosis_summary
    已存在同 id 则更新，否则新增。
    """
    try:
        metadata = req.metadata or {}
        success = rag_store(
            strategy_id=req.id,
            code=req.code,
            domain=metadata.get("domain", "unknown"),
            version=metadata.get("version", 0),
            cost=metadata.get("cost", 0.0),
            params=metadata.get("params", {}),
            diagnosis_summary=metadata.get("diagnosis_summary", ""),
        )
        return {
            "success": success,
            "message": "存储成功" if success else "存储失败",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"存储失败: {str(e)}")


@router.get("/rag/list")
async def list_strategies(limit: int = 100):
    """
    列出策略库中所有策略

    供前端在演化监控页判断"当前版本是否已存入 RAG"。
    """
    try:
        results = rag_list(limit)
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列表获取失败: {str(e)}")


@router.post("/rag/delete")
async def delete_strategy(req: DeleteRequest):
    """
    从策略库中删除指定策略
    """
    try:
        success = rag_delete(req.id)
        return {
            "success": success,
            "message": "删除成功" if success else "删除失败（策略不存在）",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")