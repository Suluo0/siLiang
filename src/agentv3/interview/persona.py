"""
PersonaManager — 面试官人设加载与 prompt 编译
"""
import os
from src.utils import load_skill

_SKILL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skills", "persona")

_PERSONA_FILES = {
    "ali_p7": "ali_p7.md",
    "tencent_t9": "tencent_t9.md",
    "bytedance_22": "bytedance_22.md",
    "foreign_friendly": "foreign_friendly.md",
    "huawei_expert": "huawei_expert.md",
    "startup_cto": "startup_cto.md",
    "meituan_l8": "meituan_l8.md",
    "campus_basic": "campus_basic.md",
    "promotion_defense": "promotion_defense.md",
    "free_mode": "free_mode.md",
}


class PersonaManager:
    """加载并编译面试官人设 prompt"""

    _cache: dict[str, str] = {}

    @classmethod
    def list_ids(cls) -> list[str]:
        return list(_PERSONA_FILES.keys())

    @classmethod
    def load_prompt(cls, persona_id: str) -> str:
        if persona_id not in _PERSONA_FILES:
            raise ValueError(f"未知的人设ID: {persona_id}，可选: {cls.list_ids()}")

        if persona_id in cls._cache:
            return cls._cache[persona_id]

        path = os.path.join(_SKILL_DIR, _PERSONA_FILES[persona_id])
        raw = load_skill(path)
        cls._cache[persona_id] = raw
        return raw

    @classmethod
    def compile_prompt(cls, persona_id: str, context: dict) -> str:
        """
        加载人设 prompt 并注入运行时上下文变量。

        context 可包含:
        - candidate_name: 候选人称呼
        - target_position: 目标岗位
        - resume_highlights: 简历亮点摘要
        - jd_core_requirements: JD 核心要求
        - round_number: 当前轮次
        - max_rounds: 最大轮次
        - extracted_context: 聚合上下文
        """
        template = cls.load_prompt(persona_id)

        template = template.replace("{{candidate_name}}", context.get("candidate_name", "面试者"))
        template = template.replace("{{target_position}}", context.get("target_position", "未知岗位"))
        template = template.replace("{{resume_highlights}}", context.get("resume_highlights", "暂无"))
        template = template.replace("{{jd_core_requirements}}", context.get("jd_core_requirements", "暂无"))
        template = template.replace("{{round_number}}", str(context.get("round_number", 1)))
        template = template.replace("{{max_rounds}}", str(context.get("max_rounds", 10)))
        template = template.replace("{{extracted_context}}", context.get("extracted_context", "暂无"))

        return template
