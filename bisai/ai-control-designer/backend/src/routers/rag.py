"""
RAG 策略库 API 路由

终版决策：B 不封装任何 RAG 逻辑。
B 在 router 中直接 from core.rag.client import get_rag_client，只做 HTTP 请求/响应转换。
D 负责 core/rag/ 全部逻辑。
"""

import sys
from pathlib import Path

# 添加 ai-control-designer1 路径以导入 D 模块
AI_CONTROL_DESIGNER1_ROOT = Path(__file__).parent.parent.parent.parent.parent / "ai-control-designer1"
if str(AI_CONTROL_DESIGNER1_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_CONTROL_DESIGNER1_ROOT))

from fastapi import APIRouter
from pydantic import BaseModel, Field

# 导入 D 模块的 RAG 功能
from core.rag.client import RAGClient
from core.rag.indexer import RAGIndexer
from core.rag.retriever import RAGRetriever

router = APIRouter(tags=["rag"])


class SearchRequest(BaseModel):
    query: str = Field(..., description="查询文本")
    top_k: int = Field(5, ge=1, le=20)
    filters: dict | None = Field(None, description="过滤条件")


class StoreRequest(BaseModel):
    id: str = Field(..., description="策略ID")
    code: str = Field(..., description="控制律代码")
    metadata: dict = Field(default_factory=dict, description="元数据（params, diagnosis, scene, domain, cost 等）")


@router.post("/rag/search")
async def search_strategies(req: SearchRequest):
    """
    检索相似控制策略

    调用 D 模块: core.rag.retriever.RAGRetriever
    """
    try:
        client = RAGClient()
        retriever = RAGRetriever(client)
        results = retriever.search(req.query, req.top_k, req.filters)
        return {
            "success": True,
            "results": results
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/rag/store")
async def store_strategy(req: StoreRequest):
    """
    存储控制策略到 RAG 策略库

    调用 D 模块: core.rag.indexer.RAGIndexer
    """
    try:
        client = RAGClient()
        indexer = RAGIndexer(client)
        success = indexer.add_strategy(req.id, req.code, req.metadata)
        return {
            "success": success
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

