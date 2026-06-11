"""
Embedding 编码器封装 (可选)
bge-large-zh-v1.5 首次下载需 ~1GB，下载失败时优雅降级
"""
import numpy as np
from typing import Optional
from src.config.settings import settings


class EmbeddingEncoder:
    _instance: Optional["EmbeddingEncoder"] = None

    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.device = settings.EMBEDDING_DEVICE
        self._model = None
        self._failed = False

    @classmethod
    def get_instance(cls) -> "EmbeddingEncoder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """重置单例，强制重新加载模型"""
        cls._instance = None

    @property
    def available(self) -> bool:
        """是否可用"""
        if self._failed:
            return False
        try:
            self._lazy_load()
            return True
        except Exception:
            self._failed = True
            return False

    def _lazy_load(self):
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self.model_name, device=self.device)

    def encode(self, text: str) -> np.ndarray:
        """将文本编码为向量，失败返回零向量"""
        if not self.available:
            return np.zeros(self.dim, dtype=np.float32)
        try:
            embedding = self._model.encode(text, normalize_embeddings=True)
            return np.array(embedding, dtype=np.float32)
        except Exception:
            return np.zeros(self.dim, dtype=np.float32)

    @property
    def dim(self) -> int:
        return 1024
