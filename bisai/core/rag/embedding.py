"""
ModelScope Embedding 适配器

支持魔搭社区的 m3e-small 等 sentence embedding 模型
"""

from typing import List

import numpy as np


class ModelScopeEmbedding:
    """
    ModelScope Embedding 提供者

    使用魔搭社区的 embedding 模型（如 m3e-small）
    首次使用会自动下载模型到缓存目录
    """

    def __init__(self, model_name: str = "AI-ModelScope/m3e-small"):
        """
        Args:
            model_name: ModelScope 模型标识符
        """
        self.model_name = model_name
        self._pipeline = None
        self._dimension = None

    def _load_model(self):
        """延迟加载模型（首次调用时加载）"""
        if self._pipeline is not None:
            return

        try:
            from modelscope.pipelines import pipeline
            from modelscope.utils.constant import Tasks

            print(f"正在加载 ModelScope embedding 模型: {self.model_name}")
            print("首次使用可能需要下载模型（约 400MB），请耐心等待...")

            self._pipeline = pipeline(
                Tasks.sentence_embedding,
                model=self.model_name
            )

            # 测试获取维度
            test_result = self._pipeline(input={'source_sentence': ["test"]})
            self._dimension = len(test_result['text_embedding'][0])

            print(f"[OK] 模型加载成功，embedding 维度: {self._dimension}")

        except ImportError as e:
            raise ImportError(
                f"请先安装 modelscope 及其依赖: pip install modelscope sentence_transformers\n"
                f"然后下载模型: modelscope download --model AI-ModelScope/m3e-small\n"
                f"错误详情: {e}"
            )
        except Exception as e:
            raise RuntimeError(f"加载 ModelScope 模型失败: {e}")

    @property
    def dimension(self) -> int:
        """返回 embedding 维度"""
        if self._dimension is None:
            self._load_model()
        return self._dimension

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        将文本列表转换为向量表示

        Args:
            texts: 文本列表

        Returns:
            embedding 向量列表，shape: (len(texts), dimension)
        """
        self._load_model()

        if hasattr(self, '_use_sentence_transformer') and self._use_sentence_transformer:
            # 使用 sentence_transformers
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.tolist()
            return embeddings
        else:
            # 使用 ModelScope pipeline
            result = self._pipeline(input={'source_sentence': texts})
            embeddings = result['text_embedding']
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.tolist()
            return embeddings

    def embed_single(self, text: str) -> List[float]:
        """嵌入单条文本"""
        return self.embed([text])[0]


# ChromaDB EmbeddingFunction 适配器
class ModelScopeEmbeddingFunction:
    """
    ChromaDB 兼容的 EmbeddingFunction

    用于传入 ChromaDB collection 的 embedding_function 参数
    """

    def __init__(self, model_name: str = "AI-ModelScope/m3e-small"):
        self._provider = ModelScopeEmbedding(model_name)

    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        ChromaDB EmbeddingFunction 接口

        Args:
            input: 文本列表

        Returns:
            embedding 向量列表
        """
        return self._provider.embed(input)
