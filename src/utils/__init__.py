"""
共享工具函数 — 余弦相似度、关键词解析、JSON清洗、技能文件加载
"""
import numpy as np


def cosine(a, b) -> float:
    """向量余弦相似度"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def parse_keywords(raw: str) -> list[str]:
    """解析逗号分隔的关键词列表"""
    if not raw:
        return []
    return [kw.strip() for kw in raw.replace("，", ",").split(",") if kw.strip()]


def clean_json(raw: str) -> str:
    """去除 LLM 输出中的 Markdown 代码围栏"""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    return raw


def load_skill(path: str) -> str:
    """加载技能 Markdown 文件"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
