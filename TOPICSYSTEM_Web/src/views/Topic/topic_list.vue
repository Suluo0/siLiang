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

    <!-- Tag 筛选栏 -->
    <div class="tag-strip">
      <el-tag v-for="t in feedTags" :key="t" size="small"
        :type="activeTag === t ? '' : 'info'"
        :effect="activeTag === t ? 'dark' : 'plain'"
        class="ftag" @click="toggleTag(t)">{{ t }}</el-tag>
      <el-button v-if="activeTag" size="small" text @click="clearTag">✕ 清除</el-button>
    </div>

    <!-- 三列信息流 -->
    <div class="feed-grid" v-loading="loading">
      <div class="feed-col" v-for="col in columns" :key="col.key">
        <div class="col-header">
          <span class="col-dot" :style="{ background: col.color }"></span>
          {{ col.label }}
          <span class="col-count">{{ col.items.length }}</span>
        </div>

        <div class="col-body">
          <div v-if="!col.items.length" class="col-empty">暂无</div>
          <div v-for="item in col.items" :key="item.id" class="card" @click="goDetail(item.id)">
            <div class="card-head">
              <span class="card-domain">{{ item.domain }}</span>
              <span class="card-diff">L{{ item.difficulty }}</span>
            </div>
            <div class="card-title">{{ item.topic }}</div>
            <div class="card-tags" v-if="item.tags?.length">
              <span v-for="tg in item.tags.slice(0, 4)" :key="tg" class="ctag">{{ tg }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { getTopicList } from '@/api/topic'

const router = useRouter()
const keyword = ref('')
const activeTag = ref('')
const loading = ref(false)
const totalTopics = ref(0)

const feedTags = ['核心能力', '并发', '锁', 'JVM', 'MySQL', 'Redis', 'Spring', '分布式',
  '消息队列', '缓存', '框架', '中间件', '架构', '数据结构', '算法', '后端', '事务']

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

function toggleTag(tag) {
  activeTag.value = activeTag.value === tag ? '' : tag
  fetchAll()
}
function clearTag() { activeTag.value = ''; fetchAll() }
function goDetail(id) { router.push(`/topic/detail/${id}`) }

onMounted(() => fetchAll())
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
  display: flex; flex-wrap: wrap; gap: 6px;
  padding-bottom: 12px; margin-bottom: 10px;
  border-bottom: 1px solid #eee;
  align-items: center; flex-shrink: 0;
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

.feed-col {
  background: #f8f9fc;
  border-radius: 14px;
  padding: 18px 16px 8px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.col-header {
  font-size: 14px; font-weight: 600; color: #333;
  margin-bottom: 12px; display: flex; align-items: center; gap: 8px;
  flex-shrink: 0;
}
.col-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.col-count { margin-left: auto; font-size: 12px; color: #aaa; font-weight: 400; }

.col-body {
  display: flex; flex-direction: column; gap: 12px;
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}
.col-body::-webkit-scrollbar { width: 5px; }
.col-body::-webkit-scrollbar-thumb { background: #ddd; border-radius: 3px; }

.col-empty {
  text-align: center; color: #ccc; font-size: 13px; padding: 30px 0;
}

/* ── 卡片 ── */
.card {
  background: #fff; border-radius: 10px; padding: 16px 18px;
  cursor: pointer; transition: all 0.2s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04); flex-shrink: 0;
}
.card:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.08); transform: translateY(-1px); }

.card-head {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px;
}
.card-domain {
  font-size: 11px; font-weight: 600; color: #6366f1;
  background: rgba(99,102,241,0.08); padding: 2px 8px; border-radius: 4px;
}
.card-diff {
  font-size: 11px; color: #aaa; font-weight: 500;
}

.card-title {
  font-size: 14px; font-weight: 600; color: #222;
  line-height: 1.5; margin-bottom: 10px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-tags {
  display: flex; flex-wrap: wrap; gap: 5px;
}
.ctag {
  font-size: 11px; color: #888; background: #f1f2f3;
  padding: 2px 8px; border-radius: 4px;
}
</style>
