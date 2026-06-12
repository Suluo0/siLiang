"""
analyze_jd capability — 解析 JD 文本，提取核心要求
"""
import json
import os
from src.tools.llm_client import LLMClient
from src.utils import clean_json

_JD_PROMPT = """你是一位资深 HR，擅长从 JD 中提取结构化信息。

## 分析维度

### position（岗位名称）
### level（岗位级别）
- 初级 / 中级 / 高级 / 专家

### requirements（核心要求列表）
- 每条要求一句话概括，5-10条

### required_skills（必备技能）
- 明确要求的技术栈

### preferred_skills（加分技能）
- 加分项

### domains（考察领域）
- 面试中会重点考察的技术领域

### soft_skills（软技能要求）
- 沟通、协作、管理等

## 输出格式

直接输出 JSON：
{
  "position": "岗位名",
  "level": "高级",
  "requirements": ["要求1"],
  "required_skills": [{"name": "Java", "level": "精通"}],
  "preferred_skills": ["技能1"],
  "domains": ["后端开发"],
  "soft_skills": ["沟通能力"],
  "summary": "一句话概述（30字）"
}
"""


async def analyze_jd(jd_text: str) -> dict:
    if not jd_text or not jd_text.strip():
        return {"position": "未知", "level": "中级", "requirements": [],
                "required_skills": [], "preferred_skills": [], "domains": [],
                "soft_skills": [], "summary": "未提供 JD"}

    llm = LLMClient.get_instance()

    raw = await llm.ainvoke(
        query=f"请分析以下 JD：\n\n{jd_text[:3000]}",
        system_prompt=_JD_PROMPT,
        temperature=0.0,
        max_tokens=1024,
        json_mode=True,
    )
    result = json.loads(clean_json(raw))
    result.setdefault("position", "未知")
    result.setdefault("level", "中级")
    result.setdefault("requirements", [])
    result.setdefault("required_skills", [])
    result.setdefault("preferred_skills", [])
    result.setdefault("domains", [])
    result.setdefault("soft_skills", [])
    result.setdefault("summary", "")

    return result
