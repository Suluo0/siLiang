<template>
  <div class="practice-page">
    <!-- 顶部:标题 + 进度 -->
    <div class="prac-head">
      <div class="head-row">
        <div class="brand">刷题</div>
        <span class="total-hint">{{ stats.total }} 道题</span>
      </div>
      <!-- 掌握进度条 -->
      <div class="progress-card">
        <div class="pc-top">
          <span class="pc-label">掌握进度</span>
          <span class="pc-num">
            <b>{{ stats.mastered }}</b> / {{ stats.total }} 已掌握
          </span>
        </div>
        <el-progress
          :percentage="masteredPct"
          :stroke-width="10"
          color="#10b981"
          :show-text="false"
        />
        <div class="pc-legend">
          <span><i class="dot ok"></i>已掌握 {{ stats.mastered }}</span>
          <span><i class="dot learning"></i>学习中 {{ stats.learning }}</span>
          <span><i class="dot none"></i>未开始 {{ Math.max(stats.total - stats.mastered - stats.learning, 0) }}</span>
        </div>
      </div>
    </div>

    <!-- 筛选 + 搜索 -->
    <div class="filter-bar">
      <div class="seg">
        <button
          v-for="f in FILTERS" :key="f.key"
          class="seg-btn" :class="{ on: filter === f.key }"
          @click="filter = f.key"
        >{{ f.label }}</button>
      </div>
      <el-input
        v-model="keyword" placeholder="搜索知识点..." class="search-box" clearable
        @input="debouncedFetch"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
    </div>

    <!-- 题目列表 -->
    <div class="topic-list" v-loading="loading">
      <div v-if="!filtered.length && !loading" class="empty">
        {{ filter === 'all' ? '暂无题目' : '该分类下暂无题目' }}
      </div>
      <div
        v-for="t in filtered" :key="t.id"
        class="topic-card" :class="{ expanded: openId === t.id }"
      >
        <div class="tc-head" @click="toggle(t.id)">
          <div class="tc-main">
            <span class="status-badge" :class="statusClass(t.user_status)">{{ statusText(t.user_status) }}</span>
            <span class="tc-title">{{ t.topic }}</span>
          </div>
          <div class="tc-meta">
            <span class="tag" v-for="tg in (t.tags || []).slice(0, 2)" :key="tg">{{ tg }}</span>
            <el-icon class="caret" :class="{ open: openId === t.id }"><ArrowDown /></el-icon>
          </div>
        </div>
        <!-- 展开:作答评分面板 -->
        <div v-if="openId === t.id" class="tc-body">
          <div class="tc-tip">
            凭记忆作答；想看标准答案可
            <a href="#" @click.prevent="goDetail(t.id)">查看详解 →</a>
          </div>
          <MasteryPanel
            :topic-id="t.id"
            @mastered="onMastered(t.id)"
            @status-change="refreshStats"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, ArrowDown } from '@element-plus/icons-vue'
import { getTopicList, getDashboardStats } from '@/api/topic'
import MasteryPanel from '@/components/Topic/MasteryPanel.vue'

const router = useRouter()
const keyword = ref('')
const loading = ref(false)
const topics = ref([])
const openId = ref(null)
const filter = ref('all')

const stats = reactive({ total: 0, mastered: 0, learning: 0 })

const FILTERS = [
  { key: 'all', label: '全部' },
  { key: 'todo', label: '未掌握' },
  { key: 'learning', label: '学习中' },
  { key: 'mastered', label: '已掌握' },
]

const masteredPct = computed(() => {
  if (!stats.total) return 0
  return Math.round((stats.mastered / stats.total) * 100)
})

const filtered = computed(() => {
  if (filter.value === 'all') return topics.value
  if (filter.value === 'mastered') return topics.value.filter(t => t.user_status === 'mastered')
  if (filter.value === 'learning') return topics.value.filter(t => t.user_status === 'learning')
  // todo = 未掌握(无状态或非 mastered)
  return topics.value.filter(t => t.user_status !== 'mastered')
})

function statusClass(s) {
  if (s === 'mastered') return 'ok'
  if (s === 'learning') return 'learning'
  return 'none'
}
function statusText(s) {
  if (s === 'mastered') return '已掌握'
  if (s === 'learning') return '学习中'
  return '未开始'
}

function toggle(id) {
  openId.value = openId.value === id ? null : id
}
function goDetail(id) { router.push(`/topic/detail/${id}`) }

function onMastered(id) {
  // 本地乐观更新状态角标
  const t = topics.value.find(x => x.id === id)
  if (t) t.user_status = 'mastered'
}

async function fetchTopics() {
  loading.value = true
  try {
    const res = await getTopicList({ keyword: keyword.value, limit: 400 })
    topics.value = (res.items || []).sort((a, b) => (a.difficulty || 0) - (b.difficulty || 0))
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function refreshStats() {
  try {
    const res = await getDashboardStats()
    stats.total = res.total_topics || 0
    stats.mastered = res.mastered || 0
    stats.learning = res.learning || 0
  } catch { /* 静默 */ }
}

let timer = null
function debouncedFetch() {
  clearTimeout(timer)
  timer = setTimeout(fetchTopics, 300)
}

onMounted(() => {
  fetchTopics()
  refreshStats()
})
</script>

<style scoped>
.practice-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px 32px 0;
  overflow: hidden;
}

/* ── 顶部 ── */
.prac-head { flex-shrink: 0; }
.head-row { display: flex; align-items: center; gap: 16px; margin-bottom: 12px; }
.brand { font-size: 22px; font-weight: 800; color: #1a1a2e; letter-spacing: -0.5px; }
.total-hint { margin-left: auto; font-size: 13px; color: #999; }

.progress-card {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 14px;
  padding: 14px 18px;
  margin-bottom: 14px;
}
.pc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.pc-label { font-size: 14px; font-weight: 600; color: #1a1a2e; }
.pc-num { font-size: 13px; color: #666; }
.pc-num b { color: #10b981; font-size: 16px; }
.pc-legend { display: flex; gap: 16px; margin-top: 10px; font-size: 12px; color: #888; }
.pc-legend span { display: inline-flex; align-items: center; gap: 5px; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot.ok { background: #10b981; }
.dot.learning { background: #f59e0b; }
.dot.none { background: #d1d5db; }

/* ── 筛选 ── */
.filter-bar {
  display: flex; align-items: center; gap: 16px;
  margin-bottom: 12px; flex-shrink: 0;
}
.seg { display: inline-flex; background: #f1f2f6; border-radius: 10px; padding: 3px; }
.seg-btn {
  border: none; background: transparent; cursor: pointer;
  padding: 6px 16px; border-radius: 8px;
  font-size: 13px; color: #666; transition: all 0.15s;
}
.seg-btn.on { background: #fff; color: #6366f1; font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.search-box { width: 280px; margin-left: auto; }
.search-box :deep(.el-input__wrapper) { border-radius: 10px; }

/* ── 列表 ── */
.topic-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.empty { text-align: center; color: #aaa; padding: 60px 0; font-size: 14px; }

.topic-card {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 12px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.topic-card.expanded { border-color: #c7d2fe; box-shadow: 0 4px 16px rgba(99,102,241,0.08); }

.tc-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; cursor: pointer; gap: 12px;
}
.tc-main { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; }
.tc-title { font-size: 15px; color: #1a1a2e; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.status-badge {
  flex-shrink: 0;
  font-size: 11px; padding: 2px 8px; border-radius: 6px; font-weight: 600;
}
.status-badge.ok { background: rgba(16,185,129,0.12); color: #10b981; }
.status-badge.learning { background: rgba(245,158,11,0.12); color: #f59e0b; }
.status-badge.none { background: #f1f2f6; color: #999; }

.tc-meta { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.tag { font-size: 11px; color: #888; background: #f5f6fa; padding: 2px 8px; border-radius: 5px; }
.caret { color: #bbb; transition: transform 0.2s; }
.caret.open { transform: rotate(180deg); }

.tc-body { padding: 0 16px 16px; border-top: 1px solid #f2f2f5; }
.tc-tip { font-size: 12px; color: #999; padding: 12px 0 4px; }
.tc-tip a { color: #6366f1; text-decoration: none; }

/* ── 移动端 ── */
@media (max-width: 767px) {
  .practice-page {
    padding: 14px 4% 0;
    height: 100%;
    overflow-y: auto;
    overflow-x: hidden;
  }
  .brand { font-size: 18px; }
  .topic-list { overflow: visible; flex: none; }
  .filter-bar { flex-wrap: wrap; gap: 10px; }
  .seg { width: 100%; justify-content: space-between; }
  .seg-btn { flex: 1; padding: 6px 4px; font-size: 12px; }
  .search-box { width: 100%; margin-left: 0; }
  .tc-title { white-space: normal; }
  .tc-meta .tag { display: none; }
}
</style>
