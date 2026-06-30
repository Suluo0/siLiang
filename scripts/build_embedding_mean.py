"""
全量构建 embedding 均值向量 μ —— whitening 用。

用途:拉取题库全部 topic 的 core_summary,逐个 encode(BGE,已 L2 归一化),求均值得到 μ,
写入 data/embedding_mean.npy + data/embedding_mean_meta.json。

μ 捕捉的是 BGE 模型的各向异性锥心方向(模型级属性,非语料特征),样本越多越稳,
建议在**有完整线上题库的环境**(1226 题)运行。幂等,可重复跑。

用法:
    python scripts/build_embedding_mean.py
"""
import asyncio
import logging
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("build_embedding_mean")


async def main() -> None:
    from src.config.database import init_db, close_db
    from src.models import Topic
    from src.tools.embedding import EmbeddingEncoder
    from src.tools.embedding_mean import set_mean

    encoder = EmbeddingEncoder.get_instance()
    if not getattr(encoder, "available", False):
        logger.error("EmbeddingEncoder 不可用(缺 API key?),无法构建 μ。中止。")
        return

    await init_db()
    try:
        topics = await Topic.all().values("id", "core_summary")
        logger.info("拉取到 %d 道题", len(topics))

        vecs = []
        for i, t in enumerate(topics, 1):
            text = (t.get("core_summary") or "").strip()
            if not text:
                continue
            try:
                v = np.asarray(encoder.encode(text), dtype=np.float32)
                if v.shape and np.linalg.norm(v) > 0:
                    vecs.append(v)
            except Exception:
                logger.warning("第 %d 题 encode 失败,跳过", i, exc_info=True)
            if i % 100 == 0:
                logger.info("进度 %d/%d,有效向量 %d", i, len(topics), len(vecs))

        if not vecs:
            logger.error("没有任何有效向量,无法构建 μ。中止。")
            return

        mu = np.mean(vecs, axis=0).astype(np.float32)
        set_mean(mu, len(vecs))
        logger.info("✅ μ 构建完成: n=%d, dim=%d, |μ|=%.4f", len(vecs), mu.shape[0], float(np.linalg.norm(mu)))
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
