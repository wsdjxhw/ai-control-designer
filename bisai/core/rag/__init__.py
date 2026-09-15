"""
RAG 模块（策略向量库）
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from core.rag.client import RAGClient
from core.rag.indexer import RAGIndexer
from core.rag.retriever import RAGRetriever
from core.rag.embedding import ModelScopeEmbedding, ModelScopeEmbeddingFunction

__all__ = [
    "RAGClient",
    "RAGIndexer",
    "RAGRetriever",
    "ModelScopeEmbedding",
    "ModelScopeEmbeddingFunction",
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
    """
    indexer = RAGIndexer()
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
    """
    retriever = RAGRetriever()
    filters = {}
    if domain_filter:
        filters["domain"] = domain_filter
    
    results = retriever.search(query, top_k, filters)
    
    if min_similarity is not None:
        results = [r for r in results if r.get("similarity", 0) >= min_similarity]
    
    return results


def delete_strategy(strategy_id: str) -> bool:
    """删除策略"""
    indexer = RAGIndexer()
    return indexer.delete_strategy(strategy_id)


def list_strategies(limit: int = 100) -> List[Dict[str, Any]]:
    """列出所有策略"""
    indexer = RAGIndexer()
    return indexer.list_strategies(limit)