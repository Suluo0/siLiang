"""
Embedding 编码器 —— 硅基流动 BGE v1.5 API
无需本地模型，不依赖 PyTorch
"""
import os
import numpy as np
from typing import Optional
import httpx
from src.config.settings import settings


class EmbeddingEncoder:
    _instance: Optional["EmbeddingEncoder"] = None

    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.api_url = settings.EMBEDDING_API_URL
        self.api_key = settings.EMBEDDING_API_KEY
        self._failed = False
        self._available: Optional[bool] = None

    @classmethod
    def get_instance(cls) -> "EmbeddingEncoder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    @property
    def available(self) -> bool:
        if self._failed:
            return False
        if self._available is not None:
            return self._available
        if not self.api_key:
            self._failed = True
            self._available = False
            return False
        self._available = True
        return True

    def encode(self, text: str) -> np.ndarray:
        """将文本编码为向量，失败返回零向量"""
        if not self.available or not text:
            return np.zeros(self.dim, dtype=np.float32)
        try:
            resp = httpx.post(
                self.api_url,
                json={
                    "model": self.model_name,
                    "input": text,
                    "encoding_format": "float",
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            if resp.status_code != 200:
                return np.zeros(self.dim, dtype=np.float32)
            data = resp.json()
            embedding = data["data"][0]["embedding"]
            vec = np.array(embedding, dtype=np.float32)
            # L2 归一化
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            return vec
        except Exception:
            return np.zeros(self.dim, dtype=np.float32)

    @property
    def dim(self) -> int:
        return 1024
