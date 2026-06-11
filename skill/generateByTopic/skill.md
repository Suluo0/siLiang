# Topic 数据生成 Skill

## 简介

本 Skill 用于根据面试主题（Topic）相关的数据库表结构，生成符合表定义的完整数据。生成的数据涵盖面试题库系统的核心实体及其关联关系。

## 数据库表结构

### 1. Topic（面试楼主表）

面试题库的核心实体，记录主题的基本信息和详细内容。

| 字段 | 类型 | 描述 | 示例 |
|------|------|------|------|
| id | UUID | 主键 | 自动生成 |
| topic | Char(255) | 主题名称/面试题 | "Python GIL 是什么" |
| alias | JSON | 别名列表 | ["全局解释器锁", "GIL机制"] |
| domain | Char(100) | 领域/学科 | "Python", "系统设计", "数据库" |
| category | Char(100) | 分类 | "语言基础", "并发编程", "网络编程" |
| tags | JSON | 标签列表 | ["高频", "进阶", "原理"] |
| difficulty | Int | 难度等级(1-5) | 1=入门, 3=中等, 5=困难 |
| mastery_level | Int | 掌握程度(0-100) | 0=未掌握, 100=精通 |
| review_count | Int | 复习次数 | 0, 1, 2, 5... |
| keywords | JSON | 关键词列表 | ["线程", "锁", "并发"] |
| core_summary | Text | 核心摘要 | 一句话概括答案要点 |
| core_points | Text | 核心知识点 | 分点列举的关键点 |
| detailed_explanation | Text | 详细解释 | 完整的答案内容 |
| agent_instructions_a/b/c | Text | AI 指导指令 | 针对不同角色的提示词 |
| code_example | Text | 代码示例 | 演示代码 |
| traps | Text | 常见陷阱 | 面试中的坑点 |
| bonuses | Text | 加分项 | 回答时的额外加分点 |
| last_reviewed | Datetime | 上次复习时间 | 可为 null |
| next_review | Datetime | 下次复习时间 | 智能计算 |
| created_at | Datetime | 创建时间 | 自动生成 |
| updated_at | Datetime | 更新时间 | 自动生成 |

### 2. TopicPrerequisite（前置知识）

学习该主题前需要掌握的前置知识。

| 字段 | 类型 | 描述 | 示例 |
|------|------|------|------|
| id | UUID | 主键 | 自动生成 |
| topic | FK(Topic) | 关联主题 | 关联到 Topic |
| content | Text | 前置知识内容 | "需要了解线程基础概念" |
| sort_order | Int | 排序 | 0, 1, 2... |

### 3. TopicCoreConcept（核心概念）

该主题必须掌握的核心概念。

| 字段 | 类型 | 描述 | 示例 |
|------|------|------|------|
| id | UUID | 主键 | 自动生成 |
| topic | FK(Topic) | 关联主题 | 关联到 Topic |
| content | Text | 核心概念内容 | "GIL 是 Python 的全局解释器锁" |
| sort_order | Int | 排序 | 0, 1, 2... |

### 4. TopicDerivative（衍生知识）

基于该主题的衍生知识点。

| 字段 | 类型 | 描述 | 示例 |
|------|------|------|------|
| id | UUID | 主键 | 自动生成 |
| topic | FK(Topic) | 关联主题 | 关联到 Topic |
| content | Text | 衍生知识内容 | "多进程替代方案" |
| sort_order | Int | 排序 | 0, 1, 2... |

### 5. TopicExtension（扩展延伸）

该主题的扩展知识点。

| 字段 | 类型 | 描述 | 示例 |
|------|------|------|------|
| id | UUID | 主键 | 自动生成 |
| topic | FK(Topic) | 关联主题 | 关联到 Topic |
| content | Text | 扩展内容 | "JIT 编译器优化" |
| sort_order | Int | 排序 | 0, 1, 2... |

### 6. TopicEvaluationAnchor（评估基准）

不同掌握程度对应的评估标准。

| 字段 | 类型 | 描述 | 示例 |
|------|------|------|------|
| id | UUID | 主键 | 自动生成 |
| topic | FK(Topic) | 关联主题 | 关联到 Topic |
| level | Char(50) | 级别名称 | "入门", "掌握", "精通" |
| content | Text | 评估标准内容 | "能说出 GIL 的基本概念" |
| sort_order | Int | 排序 | 0, 1, 2... |

### 7. TopicSimilarQuestion（相似问题）

同一主题的不同问法。

| 字段 | 类型 | 描述 | 示例 |
|------|------|------|------|
| id | UUID | 主键 | 自动生成 |
| topic | FK(Topic) | 关联主题 | 关联到 Topic |
| question | Text | 相似问题 | "为什么 Python 有 GIL" |
| answer_hint | Text | 答案提示 | 简短的答题思路 |
| sort_order | Int | 排序 | 0, 1, 2... |

### 8. TopicAdvancedQuestion（进阶问题）

基于该主题的进阶/扩展问题。

| 字段 | 类型 | 描述 | 示例 |
|------|------|------|------|
| id | UUID | 主键 | 自动生成 |
| topic | FK(Topic) | 关联主题 | 关联到 Topic |
| question | Text | 进阶问题 | "如何绕过 GIL" |
| answer_hint | Text | 答案提示 | 简短的答题思路 |
| sort_order | Int | 排序 | 0, 1, 2... |

### 9. TopicReference（参考资源）

学习该主题的参考资料。

| 字段 | 类型 | 描述 | 示例 |
|------|------|------|------|
| id | UUID | 主键 | 自动生成 |
| topic | FK(Topic) | 关联主题 | 关联到 Topic |
| title | Char(255) | 资源标题 | "Python 官方文档" |
| url | Text | 资源链接 | "https://docs.python.org/" |
| description | Text | 资源描述 | "Python 官方文档关于线程的说明" |
| sort_order | Int | 排序 | 0, 1, 2... |

### 10. TopicReviewLog（复习记录）

记录每次复习的情况。

| 字段 | 类型 | 描述 | 示例 |
|------|------|------|------|
| id | UUID | 主键 | 自动生成 |
| topic | FK(Topic) | 关联主题 | 关联到 Topic |
| review_date | Datetime | 复习日期 | 2024-01-15 10:30:00 |
| mastery_level | Int | 复习后掌握程度 | 0-100 |
| review_duration | Int | 复习时长(分钟) | 15, 30, 60 |
| notes | Text | 复习笔记 | "这次对概念理解更深入了" |

## 数据生成规则

### Topic 主表规则

1. **topic（主题名称）**
   - 格式：清晰的问题或概念描述
   - 长度：10-50 个中文字符
   - 示例："什么是 Python 的 GIL"

2. **domain（领域）**
   - 必须是常见的面试领域
   - 示例：Python, Java, Go, 系统设计, 数据库, 网络, 算法, 前端

3. **category（分类）**
   - 属于 domain 下的子分类
   - 示例：语言基础、并发编程、设计模式、SQL优化

4. **difficulty（难度）**
   - 1: 入门级（概念题）
   - 2: 基础级（简单应用）
   - 3: 中等级（原理理解）
   - 4: 进阶级（综合应用）
   - 5: 困难级（深度原理/系统设计）

5. **tags（标签）**
   - 常见标签：高频、必问、进阶、原理、实战、新人友好
   - 数量：1-4 个

6. **core_summary（一句话概括）**
   - 15-30 个中文字符
   - 必须是答案的核心要点

7. **core_points（核心知识点）**
   - 使用序号列表格式
   - 3-5 个要点
   - 每个要点清晰简洁

8. **detailed_explanation（详细解释）**
   - 结构化内容
   - 包含原理说明和实际应用
   - 可包含代码示例

9. **traps（常见陷阱）**
   - 面试中容易踩的坑
   - 2-4 条

10. **bonuses（加分项）**
    - 回答时能加分的知识点
    - 1-3 条

### 关联表数据规则

1. **前置知识 (Prerequisite)**: 2-4 条，简洁描述
2. **核心概念 (CoreConcept)**: 3-5 条，核心要点
3. **衍生知识 (Derivative)**: 2-3 条，扩展延伸
4. **扩展延伸 (Extension)**: 2-3 条，深入方向
5. **评估基准 (EvaluationAnchor)**: 3 个级别（入门/掌握/精通）
6. **相似问题 (SimilarQuestion)**: 2-3 个不同问法
7. **进阶问题 (AdvancedQuestion)**: 1-2 个延伸问题
8. **参考资源 (Reference)**: 2-3 个链接
9. **复习记录 (ReviewLog)**: 根据实际复习情况生成

## 输出格式

生成数据时，请按以下 JSON 格式输出：

```json
{
  "topic": {
    "topic": "主题名称",
    "alias": ["别名1", "别名2"],
    "domain": "领域",
    "category": "分类",
    "tags": ["标签1", "标签2"],
    "difficulty": 3,
    "mastery_level": 0,
    "review_count": 0,
    "keywords": ["关键词1", "关键词2"],
    "core_summary": "一句话概括",
    "core_points": "1. 要点一\\n2. 要点二\\n3. 要点三",
    "detailed_explanation": "详细解释内容...",
    "agent_instructions_a": "给候选人的提示...",
    "agent_instructions_b": "给面试官的提示...",
    "agent_instructions_c": "给AI评估的提示...",
    "code_example": "```python\\n代码示例\\n```",
    "traps": "1. 陷阱一\\n2. 陷阱二",
    "bonuses": "1. 加分项一\\n2. 加分项二"
  },
  "prerequisites": [
    {"content": "前置知识1", "sort_order": 0},
    {"content": "前置知识2", "sort_order": 1}
  ],
  "core_concepts": [
    {"content": "核心概念1", "sort_order": 0},
    {"content": "核心概念2", "sort_order": 1}
  ],
  "derivatives": [
    {"content": "衍生知识1", "sort_order": 0}
  ],
  "extensions": [
    {"content": "扩展内容1", "sort_order": 0}
  ],
  "evaluation_anchors": [
    {"level": "入门", "content": "入门标准", "sort_order": 0},
    {"level": "掌握", "content": "掌握标准", "sort_order": 1},
    {"level": "精通", "content": "精通标准", "sort_order": 2}
  ],
  "similar_questions": [
    {"question": "问题1", "answer_hint": "提示1", "sort_order": 0}
  ],
  "advanced_questions": [
    {"question": "进阶问题1", "answer_hint": "提示1", "sort_order": 0}
  ],
  "references": [
    {"title": "资源标题", "url": "https://...", "description": "描述", "sort_order": 0}
  ]
}
```

## 示例

输入：生成一个关于 "Python 装饰器" 的完整数据

输出：

```json
{
  "topic": {
    "topic": "Python 装饰器是什么，如何自定义装饰器",
    "alias": ["Python decorator", "装饰器函数", "函数装饰器"],
    "domain": "Python",
    "category": "语言特性",
    "tags": ["高频", "原理", "实战"],
    "difficulty": 3,
    "mastery_level": 0,
    "review_count": 0,
    "keywords": ["装饰器", "高阶函数", "闭包", "@语法糖", "wraps"],
    "core_summary": "装饰器是接受函数作为输入并返回增强函数的函数，本质是闭包的应用。",
    "core_points": "1. 装饰器本质是一个返回函数的高阶函数\n2. 装饰器通过闭包实现对原函数的增强\n3. @decorator 语法糖只是装饰器的调用简写\n4. functools.wraps 可以保留原函数元信息\n5. 可以叠加多个装饰器，执行顺序从下到上",
    "detailed_explanation": "## 装饰器详解\n\n### 基本概念\n装饰器本质上是一个函数，它接受一个函数作为参数，并返回一个新的函数。通过装饰器，我们可以在不修改原函数源代码的情况下，为函数添加额外的功能。\n\n### 实现原理\n装饰器的实现依赖于 Python 的两个特性：\n1. 函数是一等公民（函数可以赋值给变量、作为参数传递、作为返回值）\n2. 闭包（函数可以访问外部作用域的变量）\n\n### 代码示例\n```python\nimport functools\n\ndef my_decorator(func):\n    @functools.wraps(func)\n    def wrapper(*args, **kwargs):\n        print(\"Before calling\")\n        result = func(*args, **kwargs)\n        print(\"After calling\")\n        return result\n    return wrapper\n\n@my_decorator\ndef say_hello(name):\n    print(f\"Hello, {name}!\")\n    return f\"Hello, {name}!\"\n\n# 等价于\n# say_hello = my_decorator(say_hello)\n```",
    "agent_instructions_a": "回答时先解释装饰器的基本概念和原理，再展示代码示例，最后说明实际应用场景。",
    "agent_instructions_b": "追问：装饰器与闭包的关系、如何实现带参数的装饰器、类装饰器的写法。",
    "agent_instructions_c": "评估要点：是否理解装饰器本质、能否手写装饰器、是否知道 functools.wraps 的作用。",
    "code_example": "import functools\n\ndef log_decorator(func):\n    @functools.wraps(func)\n    def wrapper(*args, **kwargs):\n        print(f'Calling {func.__name__}')\n        result = func(*args, **kwargs)\n        print(f'{func.__name__} finished')\n        return result\n    return wrapper\n\n@log_decorator\ndef add(a, b):\n    return a + b",
    "traps": "1. 忘记使用 functools.wraps 导致原函数元信息丢失\n2. 在装饰器返回的wrapper中不返回原函数结果\n3. 装饰器顺序错误，@decorator2 在 @decorator1 下方时先执行 decorator1",
    "bonuses": "1. 提到类装饰器的写法 __call__ 方法\n2. 知道 functools.lru_cache 可以作为装饰器使用\n3. 了解装饰器在 Django/Flask 框架中的实际应用"
  },
  "prerequisites": [
    {"content": "理解函数作为一等公民的概念", "sort_order": 0},
    {"content": "了解闭包(Closure)的原理", "sort_order": 1},
    {"content": "掌握函数定义和调用的基本语法", "sort_order": 2},
    {"content": "了解 *args 和 **kwargs 的用法", "sort_order": 3}
  ],
  "core_concepts": [
    {"content": "装饰器本质是高阶函数，接受函数参数并返回新函数", "sort_order": 0},
    {"content": "@decorator 语法糖会将被装饰函数作为参数传入装饰器", "sort_order": 1},
    {"content": "装饰器通过闭包访问和修改被装饰函数的外部变量", "sort_order": 2},
    {"content": "functools.wraps 保留原函数的 __name__、__doc__ 等元信息", "sort_order": 3},
    {"content": "多个装饰器叠加时，从最近的一个开始依次执行", "sort_order": 4}
  ],
  "derivatives": [
    {"content": "类装饰器：使用类实现装饰器，需实现 __call__ 方法", "sort_order": 0},
    {"content": "带参数的装饰器：需要三层嵌套函数", "sort_order": 1},
    {"content": "装饰器工厂：返回装饰器的函数", "sort_order": 2}
  ],
  "extensions": [
    {"content": "functools.lru_cache：基于装饰器的缓存实现", "sort_order": 0},
    {"content": "functools.singledispatch：通用函数装饰器实现", "sort_order": 1},
    {"content": "装饰器在 Web 框架中的应用（Django/Flask 中间件）", "sort_order": 2}
  ],
  "evaluation_anchors": [
    {"level": "入门", "content": "能说出装饰器的基本概念，知道 @ 符号的作用，可以读懂简单的装饰器代码", "sort_order": 0},
    {"level": "掌握", "content": "能手写带参数的装饰器，理解闭包原理，知道 functools.wraps 的用途", "sort_order": 1},
    {"level": "精通", "content": "能实现类装饰器，理解装饰器在框架中的实际应用，能处理装饰器带来的副作用", "sort_order": 2}
  ],
  "similar_questions": [
    {"question": "装饰器的工作原理是什么？", "answer_hint": "从高阶函数和闭包的角度解释", "sort_order": 0},
    {"question": "装饰器与闭包有什么区别和联系？", "answer_hint": "装饰器是闭包的应用场景之一", "sort_order": 1},
    {"question": "@property 是如何实现的？", "answer_hint": "本质是装饰器，转换为 getter 方法", "sort_order": 2}
  ],
  "advanced_questions": [
    {"question": "如何给装饰器添加参数？比如 @retry(max_retries=3)", "answer_hint": "需要三层函数嵌套，外层接收参数，中间层接收函数，最内层是实际的wrapper", "sort_order": 0},
    {"question": "如何实现一个可以记录函数执行时间的装饰器？", "answer_hint": "在wrapper中记录开始和结束时间，计算差值", "sort_order": 1}
  ],
  "references": [
    {"title": "Python 官方文档 - functools", "url": "https://docs.python.org/3/library/functools.html", "description": "Python 内置的 functools 模块文档，包含 wraps 和 lru_cache 的详细说明", "sort_order": 0},
    {"title": "Python 装饰器完全指南", "url": "https://realpython.com/primer-on-python-decorators/", "description": "Real Python 网站的装饰器详细教程", "sort_order": 1},
    {"title": "Python 装饰器使用实例", "url": "https://www.geeksforgeeks.org/decorators-in-python/", "description": "GeeksforGeeks 的装饰器实例教程", "sort_order": 2}
  ]
}
```
