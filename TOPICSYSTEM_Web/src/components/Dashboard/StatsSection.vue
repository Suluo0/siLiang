<template>
  <section class="stats-section">
    <div class="stat-card" v-for="(stat, index) in stats" :key="index">
      <div class="stat-icon" :style="{ background: stat.bgColor }">
        <component :is="stat.icon" />
      </div>
      <div class="stat-info">
        <div class="stat-value">{{ stat.value }}</div>
        <div class="stat-label">{{ stat.label }}</div>
      </div>
      <div class="stat-trend" :class="stat.trend > 0 ? 'up' : 'down'">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
          <path v-if="stat.trend > 0" d="M12 4l8 8h-6v8h-4v-8H4l8-8z"/>
          <path v-else d="M12 20l-8-8h6V4h4v8h6l-8 8z"/>
        </svg>
        {{ Math.abs(stat.trend) }}%
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { User, Collection, Cpu, Star } from '@element-plus/icons-vue'

const stats = ref([
  { icon: User, value: '1,024', label: '学习用户', trend: 12, bgColor: 'rgba(64, 158, 255, 0.1)' },
  { icon: Collection, value: '568', label: '知识主题', trend: 8, bgColor: 'rgba(103, 194, 58, 0.1)' },
  { icon: Cpu, value: '128', label: '技能生成', trend: 24, bgColor: 'rgba(230, 162, 60, 0.1)' },
  { icon: Star, value: '89%', label: '完成率', trend: 5, bgColor: 'rgba(245, 108, 108, 0.1)' },
])
</script>

<style scoped>
.stats-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 32px;
}

.stat-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
}

.stat-label {
  font-size: 14px;
  color: #86909c;
  margin-top: 4px;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
}

.stat-trend.up {
  color: #67c23a;
  background: rgba(103, 194, 58, 0.1);
}

.stat-trend.down {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.1);
}

@media (max-width: 1024px) {
  .stats-section {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-section {
    grid-template-columns: 1fr;
  }
}
</style>
