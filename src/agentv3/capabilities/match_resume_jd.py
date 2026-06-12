"""
match_resume_jd capability — 对比简历和 JD，输出差距分析
"""
import json
from src.tools.llm_client import LLMClient
from src.utils import clean_json

_MATCH_PROMPT = """你是一位资深 HR，负责对比候选人的简历和 JD，分析能力差距。

## 分析维度

### strengths（匹配强项）
- 简历中符合 JD 要求的技能和经验

### weaknesses（能力差距）
- JD 要求但简历中欠缺的技能

### overall_fit（综合匹配度）
- 0-100 分

### suggested_focus（建议考察重点）
- 面试中应该重点考察的方向

### gap_areas（薄弱领域）
- 需要加强准备的技术领域

## 输出格式

直接输出 JSON：
{
  "strengths": ["强项1"],
  "weaknesses": ["差距1"],
  "overall_fit": 70,
  "suggested_focus": "一句话建议（30字）",
  "gap_areas": ["领域1"]
}
"""


async def match_resume_jd(resume_analysis: dict, jd_analysis: dict) -> dict:
    if not resume_analysis.get("skills") or not jd_analysis.get("required_skills"):
        return {"strengths": [], "weaknesses": [], "overall_fit": 50,
                "suggested_focus": "全面考察", "gap_areas": []}

    llm = LLMClient.get_instance()

    prompt = f"""简历分析：
{json.dumps(resume_analysis, ensure_ascii=False, indent=2)}

JD 分析：
{json.dumps(jd_analysis, ensure_ascii=False, indent=2)}

请分析两者之间的匹配度和差距。"""

    raw = await llm.ainvoke(
        query=prompt,
        system_prompt=_MATCH_PROMPT,
        temperature=0.0,
        max_tokens=512,
        json_mode=True,
    )
    result = json.loads(clean_json(raw))
    result.setdefault("strengths", [])
    result.setdefault("weaknesses", [])
    result.setdefault("overall_fit", 50)
    result.setdefault("suggested_focus", "全面考察")
    result.setdefault("gap_areas", [])

    return result
