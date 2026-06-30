<template>
  <section class="stats-section">
    <div class="stat-card" v-for="(stat, index) in cards" :key="index">
      <div class="stat-icon" :style="{ background: stat.bgColor }">
        <component :is="stat.icon" />
      </div>
      <div class="stat-info">
        <div class="stat-value" :class="{ dimmed: stat.dimmed }">{{ stat.display }}</div>
        <div class="stat-label">{{ stat.label }}</div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { Collection, CircleCheck, CircleClose, Timer } from '@element-plus/icons-vue'
import request from '@/api/request'

const emit = defineEmits(['stats-loaded'])
const authenticated = ref(false)

const stats = ref({ total_topics: 0, mastered: 0, learning: 0, today_target: 0, preferences_filled: false })

const cards = computed(() => {
  const unauth = !authenticated.value
  return [
    { icon: Collection,  display: unauth ? '登录后查看' : stats.value.total_topics,
      label: '题目数量', bgColor: 'rgba(64, 158, 255, 0.1)', dimmed: unauth },
    { icon: CircleCheck, display: unauth ? '登录后查看' : stats.value.mastered,
      label: '已掌握', bgColor: 'rgba(103, 194, 58, 0.1)', dimmed: unauth },
    { icon: CircleClose, display: unauth ? '登录后查看' : stats.value.total_topics - stats.value.mastered,
      label: '未掌握', bgColor: 'rgba(245, 108, 108, 0.1)', dimmed: unauth },
    { icon: Timer,       display: unauth ? '登录后查看' : stats.value.today_target,
      label: '今日目标', bgColor: 'rgba(230, 162, 60, 0.1)', dimmed: unauth },
  ]
})

onMounted(async () => {
  try {
    const res = await request.get('/topic/dashboard/stats')
    stats.value = res
    authenticated.value = res.authenticated !== false
    emit('stats-loaded', { pref: res.preferences_filled, auth: authenticated.value })
  } catch {
    authenticated.value = false
    emit('stats-loaded', false)
  }
})
</script>

<style scoped>
.stats-section {
  display: grid;
  /* 4 列默认,移动端自动塌成 2 列 */
  /* minmax(0,1fr) 而非 1fr:允许列收缩到 0,防止内部 nowrap 长文本把列撑出容器 */
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--sp-5);
  margin-bottom: var(--sp-7);
  /* 百分比硬限位:整个统计区永不超过父容器宽度 */
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.stat-card {
  background: var(--bg-card);
  border-radius: var(--r-xl);
  padding: var(--sp-6);
  display: flex;
  align-items: center;
  gap: var(--sp-4);
  box-shadow: var(--shadow-card);
  transition: all var(--duration-base) var(--ease-out);
  min-width: 0;
  /* 百分比硬限位:单卡永不超过所在列宽,padding 计入宽度 */
  max-width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
}

.stat-icon {
  flex: 0 0 auto;
  width: 56px;
  height: 56px;
  border-radius: var(--r-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  color: var(--text-3);
}

.stat-info {
  min-width: 0;
  flex: 1;
}

.stat-value {
  font-size: var(--fs-3xl);
  font-weight: var(--fw-bold);
  color: var(--text-1);
  line-height: 1.2;
  /* 防止 "登录后查看" 在窄列溢出 */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-value.dimmed {
  font-size: var(--fs-md);
  font-weight: var(--fw-medium);
  color: var(--text-5);
}

.stat-label {
  font-size: var(--fs-sm);
  color: var(--text-4);
  margin-top: 2px;
}

/* ─── 响应式 ─── */

/* 笔记本及以下: 2 列 */
@media (max-width: 1023px) {
  .stats-section {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--sp-4);
  }
}

/* < md 手机:仅保留前 2 张卡(题目数量 / 已掌握),左右对称两列 */
@media (max-width: 767px) {
  .stats-section {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--sp-3);
    margin-bottom: var(--sp-5);
    /* 防止内容撑出视口导致页面可横向拖动 */
    max-width: 100%;
  }
  /* 隐藏第 3、4 张卡(未掌握 / 今日目标) */
  .stat-card:nth-child(n+3) {
    display: none;
  }
  .stat-card {
    padding: var(--sp-4) var(--sp-3);
    gap: var(--sp-3);
    border-radius: var(--r-lg);
    min-width: 0;
  }
  .stat-icon {
    width: 40px;
    height: 40px;
    font-size: 20px;
    border-radius: var(--r-md);
  }
  .stat-value {
    /* 标题字号调小,两列窄空间下不溢出 */
    font-size: var(--fs-xl);
    white-space: nowrap;
  }
  .stat-value.dimmed {
    font-size: var(--fs-sm);
  }
  .stat-label {
    font-size: var(--fs-xs);
  }
}
</style>
