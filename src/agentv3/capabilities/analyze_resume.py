"""
analyze_resume capability — 解析简历文本，提取技能/经验/级别
"""
import json
import os
from src.tools.llm_client import LLMClient
from src.utils import clean_json

_RESUME_PROMPT = """你是一位资深 HR 和技术面试官，擅长从简历中提取结构化信息。

## 分析维度

### skills（技能列表）
- 列出简历中提到的所有技术技能
- 标注每个技能的掌握程度：初级/中级/高级/专家

### experience_level（总体经验级别）
- 初级（1-3年）、中级（3-5年）、高级（5-8年）、专家（8年+）
- 根据工作年限和项目复杂度综合判断

### domains（领域）
- 简历涉及的技术领域：如"后端开发"、"系统设计"、"数据分析"等

### highlights（亮点）
- 简历中最突出的 3-5 个亮点
- 包括：大厂经历、核心项目、技术成果等

### education（教育背景）
- 学历、专业、毕业院校

### certifications（证书）
- 专业认证

## 输出格式

直接输出 JSON，不要有任何其他文字：
{
  "skills": [{"name": "Python", "level": "高级"}],
  "experience_level": "高级",
  "years": 6,
  "domains": ["后端开发", "系统设计"],
  "highlights": ["亮点1"],
  "education": {"degree": "硕士", "major": "计算机科学", "school": "XX大学"},
  "certifications": ["证书1"],
  "summary": "一句话概述（30字）"
}
"""


async def analyze_resume(resume_text: str) -> dict:
    if not resume_text or not resume_text.strip():
        return {"skills": [], "experience_level": "未知", "years": 0,
                "domains": [], "highlights": [], "education": {},
                "certifications": [], "summary": "未提供简历"}

    llm = LLMClient.get_instance()

    raw = await llm.ainvoke(
        query=f"请分析以下简历：\n\n{resume_text[:3000]}",
        system_prompt=_RESUME_PROMPT,
        temperature=0.0,
        max_tokens=1024,
        json_mode=True,
    )
    result = json.loads(clean_json(raw))
    result.setdefault("skills", [])
    result.setdefault("experience_level", "中级")
    result.setdefault("years", 0)
    result.setdefault("domains", [])
    result.setdefault("highlights", [])
    result.setdefault("education", {})
    result.setdefault("certifications", [])
    result.setdefault("summary", "")

    return result
