"""
InterviewSession — 面试会话状态机

职责：
1. 初始化面试（简历/JD分析 + 人设加载 + 首题选取）
2. 处理每轮回答（评分 → 上下文提取 → 路由 → 追问生成）—— 全部通过 Registry 切面保护
3. 生成面试总结
"""
import json
from dataclasses import dataclass, field
from src.agentv3.registry import CapabilityRegistry
from src.agentv3.interview.router import decide_route, get_next_consecutive_low
from src.agentv3.interview.persona import PersonaManager

_MAX_ROUNDS = 10


@dataclass
class InterviewSession:
    """面试会话，管理一次面试的完整生命周期"""

    persona_id: str = "free_mode"
    max_rounds: int = _MAX_ROUNDS
    persona: dict = field(default_factory=dict)

    # 分析结果
    resume_analysis: dict = field(default_factory=dict)
    jd_analysis: dict = field(default_factory=dict)
    match_gap: dict = field(default_factory=dict)

    # 运行时状态
    round_number: int = 0
    consecutive_low: int = 0
    current_topic: dict | None = None
    rounds: list[dict] = field(default_factory=list)

    # 上下文聚合
    aggregated_context: dict = field(default_factory=lambda: {
        "overall_strengths": [],
        "overall_weaknesses": [],
        "trend": "稳定",
    })

    def persona_prompt(self) -> str:
        return PersonaManager.compile_prompt(self.persona_id, {
            "resume_highlights": self.resume_analysis.get("summary", ""),
            "jd_core_requirements": self.jd_analysis.get("summary", ""),
            "round_number": self.round_number,
            "max_rounds": self.max_rounds,
            "extracted_context": json.dumps(self.aggregated_context, ensure_ascii=False),
        })

    # ── 初始化 ──

    async def setup(self, resume_text: str, jd_text: str,
                    resume_analysis: dict, jd_analysis: dict, match_gap: dict,
                    first_topic: dict):
        """面试初始化——传入已分析的简历/JD/首题"""
        self.resume_analysis = resume_analysis
        self.jd_analysis = jd_analysis
        self.match_gap = match_gap
        self.current_topic = first_topic
        self.round_number = 0
        self.consecutive_low = 0
        self.rounds = []

    # ── 核心：提交回答 ──

    async def submit_answer(self, answer_text: str) -> dict:
        """
        提交用户回答，返回评分 + 路由 + 下一题。

        Returns:
            {
                "round_number": int,
                "scores": {...},
                "reasoning": str,
                "route": str,
                "next_question": str | None,
                "next_topic": dict | None,
                "final": bool,
            }
        """
        if not self.current_topic:
            raise RuntimeError("面试尚未初始化")

        self.round_number += 1

        # 1. 评分（走 Registry 切面：超时+熔断+日志）
        scores = await CapabilityRegistry.call(
            "score_answer",
            question_text=self.current_topic.get("question_text", ""),
            expected_key_points=self.current_topic.get("expected_key_points", []),
            user_answer=answer_text,
            question_difficulty=self.current_topic.get("difficulty", 3),
            persona_level=3,
        )

        # 2. 上下文提取（走 Registry 切面）
        context = await CapabilityRegistry.call(
            "extract_context",
            question_text=self.current_topic.get("question_text", ""),
            answer_text=answer_text,
            scores=scores,
        )

        # 3. 路由决策
        self.consecutive_low = get_next_consecutive_low(scores["total"], self.consecutive_low)
        route = decide_route(scores["total"], self.round_number, self.consecutive_low)

        # 4. 记录本轮
        round_record = {
            "round_number": self.round_number,
            "question_text": self.current_topic.get("question_text", ""),
            "question_type": self.current_topic.get("question_type", "initial"),
            "topic_id": self.current_topic.get("topic_id"),
            "answer_text": answer_text,
            "scores": scores,
            "context": context,
            "route": route,
        }
        self.rounds.append(round_record)

        # 5. 聚合上下文
        self._aggregate_context(context)

        # 6. 生成下一题
        next_question = None
        next_topic = None
        if route != "summary":
            followup = await CapabilityRegistry.call(
                "generate_followup",
                route=route,
                current_topic_name=self.current_topic.get("topic_name", ""),
                current_domain=self.current_topic.get("domain", ""),
                current_difficulty=self.current_topic.get("difficulty", 3),
                extracted_context=context,
                persona_level=3,
            )
            next_topic = {
                "question_text": followup.get("question_text", ""),
                "question_type": route,
                "difficulty": followup.get("difficulty", 3),
                "topic_keywords": followup.get("topic_keywords", []),
                "expected_key_points": followup.get("expected_key_points", []),
                "domain": self.current_topic.get("domain", ""),
                "topic_name": "",
                "topic_id": None,
            }
            next_question = followup.get("question_text", "")
            self.current_topic = next_topic

        return {
            "round_number": self.round_number,
            "scores": scores,
            "reasoning": scores.get("reasoning", ""),
            "route": route,
            "next_question": next_question,
            "next_topic": next_topic,
            "context": context,
            "final": route == "summary",
        }

    # ── 上下文聚合 ──

    def _aggregate_context(self, context: dict):
        if context.get("knowledge_gaps"):
            for gap in context["knowledge_gaps"]:
                if gap not in self.aggregated_context["overall_weaknesses"]:
                    self.aggregated_context["overall_weaknesses"].append(gap)
        if context.get("demonstrated_skills"):
            for skill in context["demonstrated_skills"]:
                if skill not in self.aggregated_context["overall_strengths"]:
                    self.aggregated_context["overall_strengths"].append(skill)

    # ── 总结 ──

    def summary(self) -> dict:
        """生成面试数据摘要——无 LLM 调用的纯统计"""
        if not self.rounds:
            return {"total_rounds": 0, "overall_score": 0.0, "strengths": [], "weaknesses": []}

        scores_list = [r["scores"]["total"] for r in self.rounds if r.get("scores")]

        return {
            "total_rounds": len(self.rounds),
            "overall_score": round(sum(scores_list) / len(scores_list), 4) if scores_list else 0.0,
            "accuracy_avg": round(sum(r["scores"].get("accuracy", 0) for r in self.rounds) / len(self.rounds), 4),
            "depth_avg": round(sum(r["scores"].get("depth", 0) for r in self.rounds) / len(self.rounds), 4),
            "completeness_avg": round(sum(r["scores"].get("completeness", 0) for r in self.rounds) / len(self.rounds), 4),
            "clarity_avg": round(sum(r["scores"].get("clarity", 0) for r in self.rounds) / len(self.rounds), 4),
            "practical_avg": round(sum(r["scores"].get("practical", 0) for r in self.rounds) / len(self.rounds), 4),
            "strengths": self.aggregated_context.get("overall_strengths", []),
            "weaknesses": self.aggregated_context.get("overall_weaknesses", []),
            "rounds": self.rounds,
        }
