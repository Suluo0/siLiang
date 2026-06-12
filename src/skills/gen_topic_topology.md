# 知识点拓扑关系 Skill

根据已生成的面试题内容和概念，分析并输出该题目关联的知识点拓扑。

## 核心任务

你收到的输入包含：
- 题目名称（core_concept）
- 已生成的内容（one_liner、detailed_explanation 等）
- 关键词列表

你需要输出该题目关联的知识点列表，每个知识点标注 `type`、`importance` 和 `description`。

**每个知识点必须是可独立存在的面试题标题。** 即：把这个 `name` 作为搜索关键词，能找到一道合理的面试题。

---

## type 严格定义

| type | 含义 | 判定标准 |
|------|------|---------|
| **prerequisite** | 前置知识 | "学会本题之前，必须先掌握的题目"。属于同一或相邻技术域的基础层。题目内容一定会引用这些概念。 |
| **core_concept** | 核心子概念 | 理解本题必须拆解的子概念。是本题的"组成部分"或"直接依赖的技术手段"。 |
| **extension** | 扩展延伸 | **与 prerequisite 相对的深度方向。** 同一技术域/业务场景下，比本题更深层、更专精的独立题目。例如：原理推导、源码分析、性能优化、替代方案对比。extension 和 prerequisite 形成"前→本→深"的技术纵深路径。 |
| **derivative** | 衍生变体 | **必须引入新的上下文/技术域。** 与 extension 的关键区别：extension 在同一个上下文里深度挖掘；derivative 跨越到新的场景。例如从单机 HashMap 跨到并发场景（ConcurrentHashMap）、有序场景（TreeMap）、分布式场景（Redis Hash）。 |

### type 选择决策树

```
这个知识点离开了本题的上下文，还是一个可以独立搜索的面试题吗？
  ├─ 否 → 这不是一个合格的知识点，不要输出
  └─ 是 → 它属于本题所在的技术域/业务场景吗？
          ├─ 是 → 是否比本题更深层（原理/源码/性能/替代）？
          │       ├─ 是 → extension
          │       └─ 否 → 是本题的子概念/组成部分吗？
          │               ├─ 是 → core_concept
          │               └─ 否 → 是否是本题的前置基础？
          │                       ├─ 是 → prerequisite
          │                       └─ 否 → core_concept
          └─ 否（引入新上下文/新场景/新领域）→ derivative
```

---

## Fewshot 示例

### 示例 1：HashMap底层实现

**输入**：
- 题目：HashMap底层实现
- 领域：编程基础
- 内容摘要：HashMap是Java中基于哈希表实现的Map，底层由数组+链表+红黑树组成。通过哈希函数定位数组索引，使用链地址法处理冲突。JDK 8引入红黑树优化查找。涉及扩容机制（负载因子0.75、容量翻倍）、扰动函数（高16位异或低16位）。

**正确输出**：
```json
{
  "knowledge_points": [
    {
      "name": "哈希表",
      "type": "prerequisite",
      "importance": 5,
      "description": "哈希表是HashMap的理论基础——数组+哈希函数+冲突解决的抽象模型。不先理解哈希表就无法理解HashMap为何这样设计。"
    },
    {
      "name": "哈希冲突",
      "type": "core_concept",
      "importance": 5,
      "description": "不同key映射到同一数组索引的现象。链地址法和红黑树化都是为了解决此问题，是理解HashMap设计动机的关键。"
    },
    {
      "name": "红黑树",
      "type": "core_concept",
      "importance": 4,
      "description": "自平衡二叉查找树，HashMap在桶内链表过长时转化为红黑树，保证O(log n)查找效率。理解红黑树才能理解树化阈值的含义。"
    },
    {
      "name": "链表",
      "type": "core_concept",
      "importance": 4,
      "description": "线性数据结构，HashMap使用链表处理哈希冲突。理解链表的插入/查找复杂度才能理解为什么需要树化。"
    },
    {
      "name": "ConcurrentHashMap",
      "type": "derivative",
      "importance": 3,
      "description": "HashMap的线程安全版本。引入【并发编程】这个新上下文，通过CAS和synchronized替代HashMap的锁竞争模型。"
    },
    {
      "name": "TreeMap",
      "type": "derivative",
      "importance": 2,
      "description": "基于红黑树实现的有序Map。引入【有序集合】这个新上下文，与HashMap的无序特性形成对比。"
    },
    {
      "name": "哈希算法设计",
      "type": "extension",
      "importance": 3,
      "description": "比HashMap更深层的哈希原理话题。探讨哈希函数的雪崩效应、均匀分布、碰撞概率等数学基础，是HashMap中扰动函数设计的理论源头。"
    },
    {
      "name": "HashMap扩容机制详解",
      "type": "extension",
      "importance": 4,
      "description": "在HashMap同一技术域内深入分析扩容的完整流程：负载因子选择依据、rehash性能开销、JDK 7死循环根因、JDK 8的优化策略。是准备高级面试的深度专题。"
    }
  ]
}
```

**错误示例**（这些不能作为知识点）：
- ❌ `{"name": "Java", "type": "prerequisite"}` — 太宽泛，不是可独立搜索的"一道题"
- ❌ `{"name": "扰动函数", "type": "extension"}` — 太窄，是HashMap的一个实现细节，无法作为独立题目
- ❌ `{"name": "扩容机制", "type": "extension"}` — 名称不够独立，需要带上下文才合理
- ❌ `{"name": "LinkedHashMap", "type": "derivative", "importance": 1}` — importance太低说明关联不强，不应输出

---

### 示例 2：React Hooks

**输入**：
- 题目：React Hooks
- 领域：前端开发
- 内容摘要：React Hooks是React 16.8引入的函数式组件状态管理方案，包括useState、useEffect、useContext等内置Hook，以及自定义Hook的封装。Hooks解决了类组件中this绑定复杂、逻辑复用困难等问题。依赖JavaScript闭包和Fiber架构实现。

**正确输出**：
```json
{
  "knowledge_points": [
    {
      "name": "JavaScript闭包",
      "type": "prerequisite",
      "importance": 5,
      "description": "Hooks的状态保持依赖闭包机制，useState的内部实现就是通过闭包保存状态值。不理解闭包就无法理解Hooks为什么能记住状态。"
    },
    {
      "name": "React类组件",
      "type": "prerequisite",
      "importance": 4,
      "description": "Hooks的出现是为了解决类组件的痛点（this绑定、生命周期冗余、逻辑复用难）。了解类组件才能理解Hooks的设计动机。"
    },
    {
      "name": "Fiber架构",
      "type": "core_concept",
      "importance": 4,
      "description": "React的调和引擎，Hooks的状态调度和更新队列都依赖Fiber节点的链表结构。是理解Hooks执行机制的底层基础。"
    },
    {
      "name": "useEffect",
      "type": "core_concept",
      "importance": 5,
      "description": "最核心的副作用Hook，替代了类组件的生命周期方法。依赖数组、清理函数、执行时机是面试必考点。"
    },
    {
      "name": "自定义Hook",
      "type": "core_concept",
      "importance": 4,
      "description": "封装可复用逻辑的Hook模式，是Hooks生态的核心价值——逻辑复用而非UI复用。"
    },
    {
      "name": "Vue Composition API",
      "type": "derivative",
      "importance": 3,
      "description": "Vue 3的函数式组合API。引入【Vue框架】这个新上下文，设计理念与React Hooks高度相似但实现机制不同，是跨框架对比的经典话题。"
    },
    {
      "name": "Solid.js Signals",
      "type": "derivative",
      "importance": 2,
      "description": "Solid.js的响应式原语。引入【编译时响应式】这个新上下文，与Hooks的运行时调度形成对比。"
    },
    {
      "name": "React Fiber源码解读",
      "type": "extension",
      "importance": 4,
      "description": "在React技术域内，深入Fiber的链表结构、双缓冲树、优先级调度机制，理解Hooks的mount/update阶段在Fiber中的执行路径。"
    },
    {
      "name": "前端状态管理方案对比",
      "type": "extension",
      "importance": 3,
      "description": "在状态管理技术域内，对比Hooks+Context、Redux、Zustand、Jotai等方案，深入分析各方案的适用场景和设计哲学。"
    }
  ]
}
```

---

## 输出格式（严格 JSON，直接输出，无 markdown 包裹）

```json
{
  "knowledge_points": [
    {
      "name": "独立知识点名称（可作为面试题标题）",
      "type": "prerequisite",
      "importance": 3,
      "description": "这个知识点是什么，为什么对本题有成为前置知识/核心概念/扩展/衍生"
    }
  ]
}
```

## 字段约束

| 字段 | 约束 |
|------|------|
| knowledge_points 总数 | 6-10项，覆盖四种 type |
| knowledge_points[].name | 独立知识点名称，可作为面试题标题，不超过 20 字。extension 类型必须包含足够的上下文使名称可独立存在 |
| knowledge_points[].type | prerequisite / core_concept / extension / derivative |
| knowledge_points[].importance | 1-5（5=对理解本题至关重要） |
| knowledge_points[].description | 20-60字，必须解释"为什么这个 type"（比如 derivative 要说明引入了什么新上下文，extension 要说明在哪个维度上比本题更深） |

## 质量自检清单

生成每个知识点前，问自己：
1. 这个名称脱离了本题，还能作为一个面试题标题存在吗？（不能 → 删除或改名）
2. 这个 type 符合决策树吗？（尤其是 extension ≠ 实现细节，derivative ≠ 换个名字）
3. importance 4-5 的点，本题的正文是否确实大量涉及？（没有 → 降低 importance）
4. 四种 type 是否都有覆盖？（缺少某一种 → 再想想有没有遗漏）

只输出 JSON，不要任何其他文字。
