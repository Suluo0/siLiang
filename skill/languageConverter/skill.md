# 语言转换 Skill

## 简介

本 Skill 用于将用户输入的各种表达方式转换为标准化、结构化的输出。核心原则是**保留原始语义**，仅进行表达形式的优化和结构化整理，不添加原文中不存在的信息。

## 核心原则

1. **语义保留**：只优化表达形式，不添加额外信息
2. **结构化整理**：将散乱的表达整理为规范的格式
3. **风格统一**：将口语化表达转换为标准书面语
4. **错误反馈**：当语义混乱无法处理时，返回明确的错误码

## 错误码机制

### 错误响应格式

当转换失败时，返回以下错误对象结构：

```json
{
  "success": false,
  "error": {
    "code": "SEM_2001",
    "message": "语义模糊",
    "field": "content",
    "suggestion": "请提供更明确的描述",
    "original_segment": "可能导致问题的原文片段"
  },
  "original_input": "原始输入内容",
  "partial_output": null
}
```

### 错误码分类

| 错误码 | 名称 | 说明 | 建议 |
|--------|------|------|------|
| SEM_1001 | 输入为空 | 无有效输入 | 提供具体的文本内容 |
| SEM_1002 | 输入过长 | 超过2000字符限制 | 请分段输入 |
| SEM_2001 | 语义模糊 | 无法理解意图 | 提供更明确的描述 |
| SEM_2002 | 语义冲突 | 前后矛盾 | 检查并修正矛盾表述 |
| SEM_2003 | 语义不完整 | 缺少关键要素 | 补充必要的背景信息 |
| SEM_2004 | 意图不明确 | 无法确定目标 | 说明转换的具体目的 |
| SEM_2005 | 多重意图 | 多个不同意图 | 明确主要意图或分批输入 |
| SEM_3001 | 不支持的语言 | 非中英文 | 当前仅支持中英文 |
| SEM_5001 | 服务错误 | 内部处理错误 | 请稍后重试 |

## 输出格式

### 成功响应

```json
{
  "success": true,
  "original_input": "原始输入",
  "standardized_output": "保留语义但优化后的输出",
  "language": "zh/en",
  "format_type": "formal_text/bullet_points/structured_json/question_answer/definition",
  "key_elements": [
    {
      "element": "要素名称",
      "value": "提取的要素值",
      "confidence": 0.95
    }
  ],
  "confidence": 0.92,
  "suggestions": []
}
```

### 格式类型

| format_type | 说明 |
|-------------|------|
| formal_text | 正式文本，保持原文长度和内容 |
| bullet_points | 要点列表，提取关键信息点 |
| structured_json | 结构化 JSON |
| question_answer | 问答格式 |
| definition | 定义格式 |

## 示例

### 示例 1：口语转书面语（保留语义）

**输入：**
```
HashMap吧它底层是数组加链表实现的
```

**输出：**
```json
{
  "success": true,
  "original_input": "HashMap吧它底层是数组加链表实现的",
  "standardized_output": "HashMap 底层采用数组加链表实现。",
  "language": "zh",
  "format_type": "formal_text",
  "key_elements": [
    {
      "element": "数据结构",
      "value": "HashMap",
      "confidence": 1.0
    },
    {
      "element": "实现方式",
      "value": "数组加链表",
      "confidence": 0.98
    }
  ],
  "confidence": 0.99,
  "suggestions": []
}
```

### 示例 2：散乱信息结构化（保留语义）

**输入：**
```
需要处理用户的登录请求，验证用户名密码，还要记录登录时间
```

**输出：**
```json
{
  "success": true,
  "original_input": "需要处理用户的登录请求，验证用户名密码，还要记录登录时间",
  "standardized_output": "用户登录请求处理流程：\n1. 验证用户名密码\n2. 记录登录时间",
  "language": "zh",
  "format_type": "bullet_points",
  "key_elements": [
    {
      "element": "功能",
      "value": "用户登录",
      "confidence": 1.0
    },
    {
      "element": "子功能",
      "value": "验证用户名密码",
      "confidence": 0.98
    },
    {
      "element": "附加功能",
      "value": "记录登录时间",
      "confidence": 0.95
    }
  ],
  "confidence": 0.98,
  "suggestions": []
}
```

### 示例 3：模糊描述（错误示例）

**输入：**
```
性能要好
```

**输出：**
```json
{
  "success": false,
  "error": {
    "code": "SEM_2004",
    "message": "意图不明确",
    "field": "content",
    "suggestion": "请说明在什么场景下对什么进行优化，如：查询性能、写入性能、内存占用等",
    "original_segment": "性能要好"
  },
  "original_input": "性能要好",
  "partial_output": null
}
```

### 示例 4：多意图冲突检测（错误示例）

**输入：**
```
既要支持高并发又要保证数据强一致性
```

**输出：**
```json
{
  "success": false,
  "error": {
    "code": "SEM_2002",
    "message": "语义冲突",
    "field": "consistency",
    "suggestion": "高并发与强一致性通常存在权衡，请明确业务优先级或选择折中方案（如最终一致性）",
    "original_segment": "既要支持高并发又要保证数据强一致性"
  },
  "original_input": "既要支持高并发又要保证数据强一致性",
  "partial_output": null
}
```

### 示例 5：英文字符串标准化

**输入：**
```
hashmap is fast for lookup
```

**输出：**
```json
{
  "success": true,
  "original_input": "hashmap is fast for lookup",
  "standardized_output": "HashMap provides fast lookup operations.",
  "language": "en",
  "format_type": "formal_text",
  "key_elements": [
    {
      "element": "data_structure",
      "value": "HashMap",
      "confidence": 1.0
    },
    {
      "element": "characteristic",
      "value": "fast lookup",
      "confidence": 0.97
    }
  ],
  "confidence": 0.98,
  "suggestions": []
}
```

## 约束条件

| 项目 | 限制 |
|------|------|
| 最大输入长度 | 2000 字符 |
| 支持语言 | 中文、英文 |
| 最低置信度 | 0.5（低于此值返回错误） |
| 输出语言 | 保持原输入语言 |
