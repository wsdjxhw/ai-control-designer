"""
ChromaDB 持久化客户端封装

支持 ModelScope embedding (m3e-small) 和默认 embedding
"""

import chromadb
from chromadb.config import Settings
from pathlib import Path

from core.config import CHROMA_DB_DIR
from core.rag.embedding import ModelScopeEmbeddingFunction


class RAGClient:
    """
    RAG 客户端封装

    默认使用 ModelScope m3e-small embedding（512维）
    如需使用 ChromaDB 默认 embedding，设置 use_modelscope=False
    """

    def __init__(
            self,
            persist_dir: str = None,
            collection_name: str = "control_strategies_m3e",
            use_modelscope: bool = True,
            model_name: str = "AI-ModelScope/m3e-small"
    ):
        self.persist_dir = Path(persist_dir) if persist_dir else CHROMA_DB_DIR
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        if use_modelscope:
            self._embedding_function = ModelScopeEmbeddingFunction(model_name)
            self.collection = self._get_or_create_collection(
                collection_name,
                embedding_function=self._embedding_function
            )
        else:
            self._embedding_function = None
            self.collection = self._get_or_create_collection(collection_name)

    def _get_or_create_collection(self, name: str, embedding_function=None):
        """
        获取或创建集合

        ⚠️ 修复：不再每次删除旧集合。
        - 集合已存在 → 直接 get（保留数据）
        - 集合不存在 → create（首次创建）
        """
        if embedding_function:
            try:
                return self.client.get_collection(
                    name=name,
                    embedding_function=embedding_function,
                )
            except Exception:
                print(f"     创建新集合 '{name}'（使用 ModelScope embedding，512维）")
                return self.client.create_collection(
                    name=name,
                    embedding_function=embedding_function,
                )
        else:
            try:
                return self.client.get_collection(name)
            except Exception:
                return self.client.create_collection(name=name)

    def reset_collection(self, collection_name: str = None):
        """
        删除并重建集合（仅在切换 embedding 模型时手动调用）

        ⚠️ 警告：会删除所有数据！
        """
        name = collection_name or self.collection.name
        try:
            self.client.delete_collection(name)
        except Exception:
            pass

        if hasattr(self, "_embedding_function") and self._embedding_function:
            self.collection = self.client.create_collection(
                name=name,
                embedding_function=self._embedding_function,
            )
        else:
            self.collection = self.client.create_collection(name=name)




# ========== 全局单例 ==========
_global_client: RAGClient | None = None


def get_rag_client() -> RAGClient:
    """获取全局单例 RAG 客户端（首次调用时创建）"""
    global _global_client
    if _global_client is None:
        _global_client = RAGClient()
    return _global_client


