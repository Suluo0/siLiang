# Topic 数据生成 Skill V2

## 简介

根据输入主题生成完整的面试题数据。**只输出 JSON，不输出任何其他内容。**

## 输出要求

**严格遵守以下 JSON 格式输出，不要添加任何说明文字：**

```json
{
  "topic": {
    "topic": "主题名称",
    "alias": ["别名1", "别名2"],
    "domain": "领域",
    "category": "分类",
    "tags": ["标签1", "标签2"],
    "difficulty": 3,
    "keywords": ["关键词1", "关键词2"],
    "core_summary": "一句话概括",
    "core_points": "1. 要点1\n2. 要点2\n3. 要点3",
    "detailed_explanation": "详细解释",
    "agent_instructions_a": "给候选人的提示",
    "agent_instructions_b": "给面试官的提示",
    "agent_instructions_c": "给AI评估的提示",
    "code_example": "代码示例",
    "traps": "1. 陷阱1\n2. 陷阱2",
    "bonuses": "1. 加分项1\n2. 加分项2"
  },
  "prerequisites": [
    {"content": "前置知识1", "sort_order": 0},
    {"content": "前置知识2", "sort_order": 1}
  ],
  "core_concepts": [
    {"content": "核心概念1", "sort_order": 0}
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
    {"question": "相似问题1", "answer_hint": "提示1", "sort_order": 0}
  ],
  "advanced_questions": [
    {"question": "进阶问题1", "answer_hint": "提示1", "sort_order": 0}
  ],
  "references": [
    {"title": "标题", "url": "https://...", "description": "描述", "sort_order": 0}
  ]
}
```

## 字段规范（正确示例 vs 错误示例）

### topic.topic（主题名称）

| 类型 | 示例 | 说明 |
|------|------|------|
| ✅ 正确 | "Python装饰器原理及使用" | 10-50字符，描述完整主题 |
| ✅ 正确 | "HashMap底层实现与红黑树优化" | 包含具体技术细节 |
| ❌ 错误 | "HashMap" | 太短，不足10字符 |
| ❌ 错误 | "这是一个关于Python装饰器的面试题主要用于考察候选人对函数式编程的理解" | 超过50字符 |
| ❌ 错误 | "装饰器" | 不完整，缺少上下文 |

### topic.domain（领域）

| 类型 | 示例 | 说明 |
|------|------|------|
| ✅ 正确 | "Python" | 明确技术栈 |
| ✅ 正确 | "Java" | 明确技术栈 |
| ✅ 正确 | "系统设计" | 明确领域 |
| ✅ 正确 | "数据库" | 明确领域 |
| ❌ 错误 | "编程" | 太宽泛，不够具体 |
| ❌ 错误 | "基础知识" | 无明确指向 |
| ❌ 错误 | "Python/Java/Go" | 应为单一领域，不是多选 |

### topic.difficulty（难度）

| 类型 | 示例 | 说明 |
|------|------|------|
| ✅ 正确 | 1 | 入门级（如变量声明） |
| ✅ 正确 | 3 | 中等级（如装饰器原理） |
| ✅ 正确 | 5 | 困难级（如分布式事务） |
| ❌ 错误 | 0 | 超出范围 |
| ❌ 错误 | 6 | 超出范围 |
| ❌ 错误 | "3" | 应为整数，非字符串 |
| ❌ 错误 | 3.5 | 应为整数 |

### topic.core_summary（一句话概括）

| 类型 | 示例 | 说明 |
|------|------|------|
| ✅ 正确 | "装饰器是接受函数并返回增强函数的高阶函数，本质是闭包。" | 15-30字符 |
| ✅ 正确 | "HashMap是基于哈希表实现的键值对数据结构。" | 明确技术要点 |
| ❌ 错误 | "装饰器很重要" | 不足15字符 |
| ❌ 错误 | "装饰器是Python中的一种设计模式，它可以让我们在不修改原函数的情况下动态地添加一些额外的功能，比如日志记录、性能监控、权限校验等" | 超过30字符 |
| ❌ 错误 | "闭包" | 太短 |

### topic.core_points（核心要点）

| 类型 | 示例 | 说明 |
|------|------|------|
| ✅ 正确 | "1. 装饰器本质是高阶函数\n2. 通过闭包访问外部变量\n3. @语法糖是装饰器的调用简写" | 3-5条，\n分隔 |
| ❌ 错误 | "装饰器有多个要点" | 不是列表格式 |
| ❌ 错误 | "1. 要点1\n2. 要点2\n3. 要点3\n4. 要点4\n5. 要点5\n6. 要点6" | 超过5条 |
| ❌ 错误 | "要点1\n要点2" | 没有编号 |

### topic.keywords（关键词）

| 类型 | 示例 | 说明 |
|------|------|------|
| ✅ 正确 | ["装饰器", "高阶函数", "闭包", "functools.wraps"] | 2-5个 |
| ✅ 正确 | ["HashMap", "哈希表", "红黑树", "JDK8"] | 技术相关 |
| ❌ 错误 | ["装饰器"] | 不足2个 |
| ❌ 错误 | ["装饰器", "高阶函数", "闭包", "functools.wraps", "Python", "函数式编程", "装饰器模式"] | 超过5个 |
| ❌ 错误 | "装饰器,高阶函数" | 应为数组，非字符串 |

### topic.alias（别名）

| 类型 | 示例 | 说明 |
|------|------|------|
| ✅ 正确 | ["decorator", "函数装饰器"] | 1-3个别名 |
| ✅ 正确 | ["HashMap", "哈希映射", "Hash Table"] | 技术别名 |
| ❌ 错误 | ["装饰器", "decorator", "wrapper", "function", "python"] | 超过3个 |
| ❌ 错误 | "装饰器" | 应为数组，非字符串 |
| ❌ 错误 | [] | 空数组可接受，但最好有1-3个 |

### topic.tags（标签）

| 类型 | 示例 | 说明 |
|------|------|------|
| ✅ 正确 | ["高频", "原理"] | 1-4个标签 |
| ✅ 正确 | ["必问", "进阶", "源码分析"] | 面试相关标签 |
| ❌ 错误 | ["高频", "原理", "实战", "进阶", "源码"] | 超过4个 |
| ❌ 错误 | "高频" | 应为数组 |

### evaluation_anchors.level（评估级别）

| 类型 | 示例 | 说明 |
|------|------|------|
| ✅ 正确 | "入门" | 三级评估 |
| ✅ 正确 | "掌握" | 三级评估 |
| ✅ 正确 | "精通" | 三级评估 |
| ❌ 错误 | "初级" | 与标准不一致 |
| ❌ 错误 | "专家" | 与标准不一致 |
| ❌ 错误 | "入门,掌握" | 应为单一值 |

### references.url（参考链接）

| 类型 | 示例 | 说明 |
|------|------|------|
| ✅ 正确 | "https://docs.python.org/3/library/functools.html" | 官方文档 |
| ✅ 正确 | "https://realpython.com/decorators/" | 有效URL |
| ❌ 错误 | "python文档" | 不是URL格式 |
| ❌ 错误 | "http://" | 无效URL |
| ❌ 错误 | "www.example.com" | 缺少协议 |

## 示例

输入：Python装饰器原理

输出：
```json
{
  "topic": {
    "topic": "Python装饰器原理及使用",
    "alias": ["decorator", "函数装饰器"],
    "domain": "Python",
    "category": "语言特性",
    "tags": ["高频", "原理"],
    "difficulty": 3,
    "keywords": ["装饰器", "高阶函数", "闭包", "functools.wraps"],
    "core_summary": "装饰器是接受函数并返回增强函数的高阶函数，本质是闭包。",
    "core_points": "1. 装饰器本质是高阶函数\\n2. 通过闭包访问外部变量\\n3. @语法糖是装饰器的调用简写\\n4. functools.wraps保留原函数元信息\\n5. 多装饰器从下到上执行",
    "detailed_explanation": "装饰器在不改动原函数代码的情况下为其添加新功能...",
    "agent_instructions_a": "先解释概念，再演示代码，最后说明应用场景。",
    "agent_instructions_b": "追问带参装饰器、类装饰器、装饰器副作用。",
    "agent_instructions_c": "评估要点：理解装饰器本质、能手写装饰器、知道wraps作用。",
    "code_example": "import functools\\ndef log(func):\\n    @functools.wraps(func)\\n    def wrapper(*args, **kwargs):\\n        print(f'Calling {func.__name__}')\\
n        return func(*args, **kwargs)
    return wrapper

@log
def add(a, b):
    return a + b",
    "traps": "1. 忘记使用functools.wraps\\n2. wrapper不返回原函数结果\\n3. 装饰器顺序错误",
    "bonuses": "1. 提到类装饰器\\n2. 知道lru_cache装饰器\\n3. 了解框架中间件"
  },
  "prerequisites": [
    {"content": "函数作为一等公民", "sort_order": 0},
    {"content": "闭包原理", "sort_order": 1},
    {"content": "*args和**kwargs用法", "sort_order": 2}
  ],
  "core_concepts": [
    {"content": "装饰器是接受函数参数并返回新函数的高阶函数", "sort_order": 0},
    {"content": "@decorator语法糖将被装饰函数作为参数传入装饰器", "sort_order": 1},
    {"content": "functools.wraps保留原函数__name__和__doc__等元信息", "sort_order": 2}
  ],
  "derivatives": [
    {"content": "类装饰器：实现__call__方法的类", "sort_order": 0},
    {"content": "带参装饰器：三层嵌套函数", "sort_order": 1}
  ],
  "extensions": [
    {"content": "functools.lru_cache基于装饰器的缓存", "sort_order": 0},
    {"content": "Django/Flask中间件本质是装饰器", "sort_order": 1}
  ],
  "evaluation_anchors": [
    {"level": "入门", "content": "能说出装饰器基本概念，知道@符号作用", "sort_order": 0},
    {"level": "掌握", "content": "能手写装饰器，理解闭包原理，知道wraps用途", "sort_order": 1},
    {"level": "精通", "content": "能实现类装饰器，理解框架装饰器应用", "sort_order": 2}
  ],
  "similar_questions": [
    {"question": "装饰器的工作原理是什么？", "answer_hint": "高阶函数+闭包角度解释", "sort_order": 0},
    {"question": "@property是如何实现的？", "answer_hint": "本质是装饰器转为getter", "sort_order": 1}
  ],
  "advanced_questions": [
    {"question": "如何实现带参数的装饰器？", "answer_hint": "三层函数嵌套", "sort_order": 0}
  ],
  "references": [
    {"title": "Python官方文档", "url": "https://docs.python.org.org/3/library/functools.html", "description": "functools模块文档", "sort_order": 0}
  ]
}
```

## 重要约束

1. **只输出JSON**，不要有任何前缀、后缀、说明文字
2. **JSON必须完整**，所有括号、引号必须配对
3. **字符串内换行使用\\n**，不要使用实际换行
4. **代码示例在JSON字符串内**，用\\n表示换行
