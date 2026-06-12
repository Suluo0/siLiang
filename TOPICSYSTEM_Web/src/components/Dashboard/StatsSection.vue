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
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 32px;
}
.stat-card {
  background: #fff; border-radius: 16px; padding: 24px;
  display: flex; align-items: center; gap: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04); transition: all 0.3s;
}
.stat-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
.stat-icon {
  width: 56px; height: 56px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center; font-size: 26px; color: #555;
}
.stat-value { font-size: 28px; font-weight: 700; color: #1a1a2e; }
.stat-value.dimmed { font-size: 14px; font-weight: 500; color: #bbb; }
.stat-label { font-size: 13px; color: #999; margin-top: 2px; }
</style>
