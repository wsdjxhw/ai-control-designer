"""
RAG 模块（策略向量库）
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from core.rag.client import RAGClient, get_rag_client
from core.rag.indexer import RAGIndexer
from core.rag.retriever import RAGRetriever
from core.rag.embedding import ModelScopeEmbedding, ModelScopeEmbeddingFunction

__all__ = [
    "RAGClient",
    "RAGIndexer",
    "RAGRetriever",
    "ModelScopeEmbedding",
    "ModelScopeEmbeddingFunction",
    "get_rag_client",
    "store_strategy",
    "search_strategies",
    "delete_strategy",
    "list_strategies",
]


# ========== 快捷工具函数 ==========

def store_strategy(
    strategy_id: str,
    code: str,
    domain: str,
    version: int,
    cost: float,
    params: Dict[str, float],
    diagnosis_summary: str = ""
) -> bool:
    """
    快捷入库函数（供 C 模块调用）

    🆕 使用全局单例 RAG 客户端，避免每次调用重建 ChromaDB 连接
    """
    indexer = RAGIndexer(client=get_rag_client())
    metadata = {
        "domain": domain,
        "version": version,
        "cost": cost,
        "params": params,
        "diagnosis_summary": diagnosis_summary,
        "created_at": datetime.now().isoformat()
    }
    return indexer.add_strategy(strategy_id, code, metadata)


def search_strategies(
    query: str,
    top_k: int = 5,
    domain_filter: Optional[str] = None,
    min_similarity: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    快捷检索函数

    🆕 使用全局单例 RAG 客户端
    """
    retriever = RAGRetriever(client=get_rag_client())
    filters = {}
    if domain_filter:
        filters["domain"] = domain_filter

    results = retriever.search(query, top_k, filters)

    if min_similarity is not None:
        results = [r for r in results if r.get("similarity", 0) >= min_similarity]

    return results


def delete_strategy(strategy_id: str) -> bool:
    """删除策略（🆕 使用全局单例）"""
    indexer = RAGIndexer(client=get_rag_client())
    return indexer.delete_strategy(strategy_id)


def list_strategies(limit: int = 100) -> List[Dict[str, Any]]:
    """列出所有策略（🆕 使用全局单例）"""
    indexer = RAGIndexer(client=get_rag_client())
    return indexer.list_strategies(limit)