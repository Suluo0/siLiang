"""
Embedding 均值向量(μ)单一入口 —— whitening 减均值 + 增量更新。

为什么需要:BGE 这类中文 dense embedding 存在各向异性(anisotropy / cone effect),
所有句向量挤在向量空间一个窄锥里,任意两段中文余弦天然落在 0.4~0.7,绝对余弦值
几乎不携带"掌握度"信息。减去全局均值方向 μ 可打掉一阶各向异性,让好/坏答案的
余弦拉开区分度。

μ 捕捉的是模型级属性(锥心方向),不是某批题目的内容特征,因此收敛极快、几乎不漂移。

文件落地:
  data/embedding_mean.npy        —— μ 向量(float32, dim=1024)
  data/embedding_mean_meta.json  —— {"n": 样本数, "dim": 维度}

μ 缺失时 whiten() 退化为恒等(原样返回),并打一次 warn 日志,保证无 μ 环境
(本地 / 测试 / 冷启动)也能正常评分,只是少了各向异性矫正。
"""
import json
import logging
import threading
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_DIM = 1024
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_MU_PATH = _DATA_DIR / "embedding_mean.npy"
_META_PATH = _DATA_DIR / "embedding_mean_meta.json"

_lock = threading.Lock()
_mu: np.ndarray | None = None
_n: int = 0
_loaded = False
_warned = False


def _ensure_loaded() -> None:
    """模块级懒加载 μ(只读一次磁盘)。"""
    global _mu, _n, _loaded
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
        try:
            if _MU_PATH.exists():
                _mu = np.load(_MU_PATH).astype(np.float32)
                if _META_PATH.exists():
                    meta = json.loads(_META_PATH.read_text(encoding="utf-8"))
                    _n = int(meta.get("n", 0))
                logger.info("embedding μ 已加载: n=%d, dim=%d", _n, _mu.shape[0])
            else:
                _mu = None
        except Exception:
            logger.warning("加载 embedding μ 失败,whitening 将退化为恒等", exc_info=True)
            _mu = None
        _loaded = True


def is_available() -> bool:
    _ensure_loaded()
    return _mu is not None


def whiten(v: np.ndarray) -> np.ndarray:
    """对单个向量做减均值白化。μ 缺失时原样返回(退化为恒等)。"""
    global _warned
    _ensure_loaded()
    if _mu is None:
        if not _warned:
            logger.warning("embedding μ 缺失,whitening 已退化为恒等。"
                           "请在有线上题库的环境运行 scripts/build_embedding_mean.py 构建 μ。")
            _warned = True
        return v
    if v is None or v.shape != _mu.shape:
        return v
    return (v - _mu).astype(np.float32)


def set_mean(mu: np.ndarray, n: int) -> None:
    """全量构建:直接覆盖 μ 与样本数(由 build_embedding_mean.py 调用)。幂等。"""
    global _mu, _n, _loaded
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    mu = mu.astype(np.float32)
    np.save(_MU_PATH, mu)
    _META_PATH.write_text(json.dumps({"n": int(n), "dim": int(mu.shape[0])},
                                     ensure_ascii=False), encoding="utf-8")
    with _lock:
        _mu, _n, _loaded = mu, int(n), True
    logger.info("embedding μ 已写入: n=%d, dim=%d", n, mu.shape[0])


def update_mean(vectors: list[np.ndarray]) -> None:
    """
    增量均值更新,数学上与全量重算等价,每个新向量 O(1):
        μ' = (N·μ + Σvᵢ) / (N + K),  N' = N + K
    挂在题目生成管道写库步骤后,题库增长时 μ 自动跟进、零额外成本、永不漂移。
    μ 文件不存在时静默跳过(等首次全量 build 后才有意义)。
    """
    global _mu, _n
    _ensure_loaded()
    if _mu is None:
        return  # 还没全量构建过,增量无意义,跳过
    vecs = [v.astype(np.float32) for v in vectors
            if v is not None and v.shape == _mu.shape and np.linalg.norm(v) > 0]
    if not vecs:
        return
    with _lock:
        k = len(vecs)
        summed = np.sum(vecs, axis=0)
        new_mu = (_n * _mu + summed) / (_n + k)
        new_n = _n + k
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        np.save(_MU_PATH, new_mu.astype(np.float32))
        _META_PATH.write_text(json.dumps({"n": int(new_n), "dim": int(new_mu.shape[0])},
                                         ensure_ascii=False), encoding="utf-8")
        _mu, _n = new_mu.astype(np.float32), new_n
    logger.info("embedding μ 增量更新: +%d → n=%d", k, new_n)
