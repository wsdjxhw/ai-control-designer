"""
控制律策略检索模块
"""

from typing import Optional, List, Dict, Any
from core.rag.client import RAGClient


class RAGRetriever:
    def __init__(self, client: RAGClient = None):
        self.client = client or RAGClient()
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        语义检索控制律策略
        """
        try:
            # 如果 filters 为空字典或 None，则不传 where
            where_condition = filters if filters else None
            results = self.client.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_condition
            )
            
            formatted = []
            if results and results['ids']:
                for i in range(len(results['ids'][0])):
                    distance = results['distances'][0][i] if results['distances'] else 1.0
                    # 🆕 用 exp(-distance) 让相似度更平滑地映射到 (0, 1]
                    import math
                    similarity = math.exp(-distance / 10.0)
                    formatted.append({
                        "id": results['ids'][0][i],
                        "code": results['documents'][0][i] if results['documents'] else "",
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "similarity": similarity
                    })
            return formatted
        except Exception as e:
            print(f"RAG 检索失败: {e}")
            return []