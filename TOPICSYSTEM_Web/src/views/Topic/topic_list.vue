<template>
  <div class="feed-page">
    <!-- 顶部搜索条 -->
    <div class="top-bar">
      <div class="brand">题库</div>
      <el-input v-model="keyword" placeholder="搜索知识点..." class="search-box" clearable @input="fetchAll">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <span class="total-hint">{{ totalTopics }} 道题</span>
    </div>

    <!-- Tag 筛选栏:先选维度,再展开该维度下的细标签 -->
    <div class="tag-strip">
      <!-- 维度按钮行 -->
      <div class="dim-row">
        <el-tag
          v-for="d in dimensions" :key="d.key" size="small"
          :type="activeDim === d.key ? '' : 'info'"
          :effect="activeDim === d.key ? 'dark' : 'plain'"
          class="dim-tag" @click="toggleDim(d.key)">
          {{ d.label }}
          <span class="dim-count">{{ d.tags.length }}</span>
        </el-tag>
        <el-button v-if="activeTag || activeDim" size="small" text @click="clearAll">✕ 清除</el-button>
      </div>

      <!-- 选中维度后展开其细标签 -->
      <div v-if="activeDim && currentDimTags.length" class="sub-row">
        <el-tag
          v-for="t in currentDimTags" :key="t" size="small"
          :type="activeTag === t ? '' : 'info'"
          :effect="activeTag === t ? 'dark' : 'plain'"
          class="ftag" @click="toggleTag(t)">{{ t }}</el-tag>
      </div>
    </div>

    <!-- 三列信息流:每列复用 Category 组件 -->
    <div class="feed-grid" v-loading="loading">
      <Category
        v-for="col in columns" :key="col.key"
        :label="col.label" :color="col.color" :items="col.items"
        @card-click="goDetail" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { getTopicList, getTopicTags } from '@/api/topic'
import Category from '@/components/Topic/Category.vue'

const router = useRouter()
const keyword = ref('')
const activeTag = ref('')
const activeDim = ref('')
const loading = ref(false)
const totalTopics = ref(0)
const feedTags = ref([])

// 从 API 加载标签
onMounted(async () => {
  try {
    const res = await getTopicTags()
    feedTags.value = res.tags || []
  } catch { /* 静默降级 */ }
  fetchAll()
})

// ── 维度分类:把后端扁平标签按技术栈归到通用维度 ──
// 每个维度的成员标签(命中即归入);未命中的归到"其他"
const DIM_DEF = [
  { key: 'java',    label: 'Java 基础', members: ['Java', '基础', '基础语法', '面向对象', '反射', '注解', '泛型', '集合', '容器', '异常', 'IO', '序列化'] },
  { key: 'concurrent', label: '并发 & JVM', members: ['并发', '锁', '线程安全', '线程', '多线程', 'JUC', 'JVM', 'GC', '内存模型', '类加载', '垃圾回收'] },
  { key: 'db',      label: '数据库', members: ['MySQL', 'Redis', 'SQL', '索引', '事务', '存储', 'NoSQL', '关系型数据库', '存储层', '数据库', '锁机制', 'B+树', '隔离级别'] },
  { key: 'frame',   label: '框架 & 中间件', members: ['框架', 'Spring', 'SpringBoot', 'SpringCloud', 'MyBatis', '中间件', '消息队列', 'RabbitMQ', 'Kafka', '缓存', 'ORM'] },
  { key: 'infra',   label: '分布式 & 架构', members: ['分布式', '架构', '高可用', '一致性', 'RPC', '微服务', '服务治理', '网关', '配置中心', '注册中心', '服务发现', '负载均衡', '限流', '熔断', '降级', '稳定性', '幂等', '可观测性', '链路追踪'] },
  { key: 'algo',    label: '数据结构 & 算法', members: ['数据结构', '算法', '排序', '查找', '树', '图', '动态规划', '链表', '哈希', '栈', '队列'] },
]

// 计算每个维度实际拥有的标签(交集:后端返回的标签 ∩ 维度成员)+ "其他"兜底
const dimensions = computed(() => {
  const all = feedTags.value || []
  const claimed = new Set()
  const dims = DIM_DEF.map(d => {
    const tags = all.filter(t => d.members.includes(t))
    tags.forEach(t => claimed.add(t))
    return { key: d.key, label: d.label, tags }
  }).filter(d => d.tags.length)  // 没有任何标签的维度不显示
  // 未被任何维度认领的标签 → 其他
  const rest = all.filter(t => !claimed.has(t))
  if (rest.length) dims.push({ key: '__other', label: '其他', tags: rest })
  return dims
})

// 当前选中维度下的细标签
const currentDimTags = computed(() => {
  const d = dimensions.value.find(x => x.key === activeDim.value)
  return d ? d.tags : []
})

const columns = reactive([
  { key: 'core',  label: '核心能力', color: '#6366f1', items: [] },
  { key: 'mid',   label: '框架 & 中间件', color: '#f59e0b', items: [] },
  { key: 'infra', label: '分布式 & 架构', color: '#10b981', items: [] },
])

const COL_MAP = {
  core:  ['核心能力', '数据结构', '算法', 'JVM', 'GC', '并发', '锁', '线程安全', 'Java', '基础', '集合', '容器', '基础语法', '面向对象', '反射', '注解', '泛型'],
  mid:   ['框架', 'Spring', 'SpringBoot', '中间件', 'Redis', 'MySQL', '存储', '消息队列', 'RabbitMQ', '缓存', 'NoSQL', '关系型数据库', 'SQL', '存储层', '后端'],
  infra: ['分布式', '架构', '高可用', '一致性', 'RPC', '微服务', '服务治理', '网关', '配置中心', '注册中心', '服务发现', '负载均衡', '限流', '熔断', '降级', '稳定性', '幂等', '可观测性', '链路追踪'],
}

function assignCol(tags) {
  if (!tags) return 'core'
  for (const tg of tags) {
    for (const [col, tlist] of Object.entries(COL_MAP)) {
      if (tlist.includes(tg)) return col
    }
  }
  return 'core'
}

async function fetchAll() {
  loading.value = true
  try {
    const params = { keyword: keyword.value, limit: 400 }
    if (activeTag.value) params.tag = activeTag.value
    const res = await getTopicList(params)
    const items = res.items || []
    totalTopics.value = res.total || 0

    columns.forEach(c => c.items = [])
    // 按难度排序
    const sorted = [...items].sort((a, b) => (a.difficulty || 0) - (b.difficulty || 0))
    for (const item of sorted) {
      const col = assignCol(item.tags)
      const target = columns.find(c => c.key === col)
      if (target && target.items.length < 30) target.items.push(item)
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

// 切换维度:展开/收起该维度的细标签;收起时清掉已选细标签
function toggleDim(key) {
  if (activeDim.value === key) {
    activeDim.value = ''
    if (activeTag.value) { activeTag.value = ''; fetchAll() }
  } else {
    activeDim.value = key
  }
}
function toggleTag(tag) {
  activeTag.value = activeTag.value === tag ? '' : tag
  fetchAll()
}
function clearAll() {
  activeDim.value = ''
  if (activeTag.value) { activeTag.value = ''; fetchAll() }
}
function goDetail(id) { router.push(`/topic/detail/${id}`) }
</script>

<style scoped>
.feed-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px 32px 0;
  overflow: hidden;
}

/* ── 顶部 ── */
.top-bar {
  display: flex; align-items: center; gap: 20px;
  margin-bottom: 10px; flex-shrink: 0;
}
.brand { font-size: 22px; font-weight: 800; color: #1a1a2e; letter-spacing: -0.5px; }
.search-box { width: 360px; }
.search-box :deep(.el-input__wrapper) { border-radius: 10px; }
.total-hint { margin-left: auto; font-size: 13px; color: #999; }

/* ── Tag 条 ── */
.tag-strip {
  padding-bottom: 12px; margin-bottom: 10px;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}
.dim-row {
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
}
.dim-tag {
  cursor: pointer; border-radius: 8px; transition: all 0.15s;
  font-size: 13px; font-weight: 600; padding: 0 12px; height: 28px; line-height: 26px;
}
.dim-tag:hover { transform: translateY(-1px); box-shadow: 0 2px 6px rgba(0,0,0,0.08); }
.dim-count {
  margin-left: 5px; font-size: 11px; font-weight: 400; opacity: 0.65;
}
.sub-row {
  display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
  margin-top: 10px; padding-top: 10px; border-top: 1px dashed #eee;
}
.ftag { cursor: pointer; border-radius: 6px; transition: all 0.15s; font-size: 12px; }
.ftag:hover { transform: translateY(-1px); box-shadow: 0 2px 6px rgba(0,0,0,0.08); }

/* ── 三列网格（占满剩余高度）── */
.feed-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* 列内样式(.feed-col / .card 等)已抽到 components/Topic/Category.vue */

/* ─── 响应式:移动端单列 ─── */
@media (max-width: 767px) {
  .feed-page {
    padding: 14px 4% 0;
    /* 移动端改为整页纵向滚动,不再锁死高度 */
    height: 100%;
    overflow-y: auto;
    overflow-x: hidden;
  }

  /* 顶部栏:标题 + 搜索 + 计数 竖向收敛 */
  .top-bar {
    flex-wrap: wrap; gap: 10px; margin-bottom: 8px;
  }
  .brand { font-size: 18px; }
  .search-box { width: 100%; order: 3; }
  .total-hint { margin-left: auto; }

  /* 标签维度按钮:横向铺开但不撑出屏幕 */
  .dim-row { gap: 6px; }
  .dim-tag {
    font-size: 12px; padding: 0 10px; height: 26px; line-height: 24px;
  }

  /* 关键:单列,三个分类区上下纵向堆叠(不再横排挤出屏幕) */
  .feed-grid {
    grid-template-columns: 1fr;
    gap: 14px;
    flex: none;
    overflow: visible;
    max-width: 100%;
  }
  /* 列内移动端样式(.feed-col / .col-body / .card)已在 Category.vue 内处理 */
}
</style>
