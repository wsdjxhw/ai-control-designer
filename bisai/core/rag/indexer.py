"""
控制律策略入库模块
"""

import json
from typing import Dict, Any
from core.rag.client import RAGClient


class RAGIndexer:
    def __init__(self, client: RAGClient = None):
        self.client = client or RAGClient()
    
    def add_strategy(self, strategy_id: str, code: str, metadata: Dict[str, Any]) -> bool:
        """
        将控制律策略入库（存在则更新，不存在则新增）
        """
        try:
            # 将 metadata 中的 dict 值转为 JSON 字符串，因为 ChromaDB 不支持 dict
            processed_metadata = {}
            for k, v in metadata.items():
                if isinstance(v, dict):
                    processed_metadata[k] = json.dumps(v, ensure_ascii=False)
                else:
                    processed_metadata[k] = v

            existing = self.client.collection.get(ids=[strategy_id])
            if existing and existing['ids']:
                self.client.collection.update(
                    ids=[strategy_id],
                    documents=[code],
                    metadatas=[processed_metadata]
                )
            else:
                self.client.collection.add(
                    ids=[strategy_id],
                    documents=[code],
                    metadatas=[processed_metadata]
                )
            return True
        except Exception as e:
            print(f"策略入库失败: {e}")
            return False
    
    def delete_strategy(self, strategy_id: str) -> bool:
        """删除策略"""
        try:
            self.client.collection.delete(ids=[strategy_id])
            return True
        except Exception as e:
            print(f"策略删除失败: {e}")
            return False
    
    def list_strategies(self, limit: int = 100) -> list:
        """列出所有策略"""
        try:
            results = self.client.collection.get(limit=limit)
            formatted = []
            if results and results['ids']:
                for i in range(len(results['ids'])):
                    formatted.append({
                        "id": results['ids'][i],
                        "code": results['documents'][i] if results['documents'] else "",
                        "metadata": results['metadatas'][i] if results['metadatas'] else {}
                    })
            return formatted
        except Exception as e:
            print(f"列出策略失败: {e}")
            return []