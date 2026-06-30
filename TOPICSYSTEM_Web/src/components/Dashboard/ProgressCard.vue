<template>
  <div class="content-card">
    <div class="card-header">
      <h2 class="card-title">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
        </svg>
        学习进度
      </h2>
    </div>
    <div class="progress-overview">
      <div class="progress-ring">
        <svg viewBox="0 0 100 100">
          <defs>
            <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style="stop-color:#667eea"/>
              <stop offset="100%" style="stop-color:#764ba2"/>
            </linearGradient>
          </defs>
          <circle class="ring-bg" cx="50" cy="50" r="45"/>
          <circle 
            class="ring-fill" 
            cx="50" 
            cy="50" 
            r="45" 
            stroke="url(#progressGradient)"
            :stroke-dasharray="283" 
            :stroke-dashoffset="96"
          />
        </svg>
        <div class="ring-text">
          <span class="ring-value">68%</span>
          <span class="ring-label">完成度</span>
        </div>
      </div>
    </div>
    <div class="progress-list">
      <div class="progress-item" v-for="p in learningProgress" :key="p.id">
        <div class="progress-icon" :style="{ background: p.color }">
          <el-icon><Cpu /></el-icon>
        </div>
        <div class="progress-info">
          <span class="progress-name">{{ p.name }}</span>
          <div class="progress-bar-small">
            <div class="progress-fill-small" :style="{ width: p.progress + '%' }"></div>
          </div>
        </div>
        <span class="progress-percent">{{ p.progress }}%</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Cpu } from '@element-plus/icons-vue'

const learningProgress = ref([
  { id: 1, name: 'Python 基础', progress: 85, color: 'rgba(64, 158, 255, 0.1)' },
  { id: 2, name: 'Web 开发', progress: 62, color: 'rgba(103, 194, 58, 0.1)' },
  { id: 3, name: '数据库', progress: 45, color: 'rgba(230, 162, 60, 0.1)' },
])
</script>

<style scoped>
.content-card {
  background: var(--bg-card);
  border-radius: var(--r-xl);
  padding: var(--sp-6);
  box-shadow: var(--shadow-card);
  min-width: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--sp-5);
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--fs-xl);
  font-weight: var(--fw-semibold);
  color: var(--text-1);
  margin: 0;
}

.card-title svg {
  color: var(--color-primary);
  flex-shrink: 0;
}

.progress-overview {
  display: flex;
  justify-content: center;
  margin-bottom: var(--sp-6);
}

.progress-ring {
  position: relative;
  width: 140px;
  height: 140px;
}

.progress-ring svg {
  transform: rotate(-90deg);
  width: 100%;
  height: 100%;
}

.ring-bg {
  fill: none;
  stroke: var(--bg-tag);
  stroke-width: 8;
}

.ring-fill {
  fill: none;
  stroke-width: 8;
  stroke-linecap: round;
  transition: stroke-dashoffset 1s ease;
}

.ring-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.ring-value {
  display: block;
  font-size: var(--fs-4xl);
  font-weight: var(--fw-bold);
  color: var(--text-1);
}

.ring-label {
  font-size: var(--fs-xs);
  color: var(--text-4);
}

.progress-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.progress-item {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  min-width: 0;
}

.progress-icon {
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  border-radius: var(--r-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.progress-info {
  flex: 1;
  min-width: 0;
}

.progress-name {
  font-size: var(--fs-md);
  color: var(--text-1);
  margin-bottom: 6px;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.progress-bar-small {
  width: 100%;
  height: 6px;
  background: var(--bg-tag);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill-small {
  height: 100%;
  background: var(--gradient-brand);
  border-radius: 3px;
  transition: width var(--duration-slow) var(--ease-out);
}

.progress-percent {
  font-size: var(--fs-md);
  font-weight: var(--fw-semibold);
  color: var(--color-primary);
  flex-shrink: 0;
}

@media (max-width: 767px) {
  .content-card {
    padding: var(--sp-4);
    border-radius: var(--r-lg);
  }
  .progress-ring {
    width: 120px;
    height: 120px;
  }
  .ring-value {
    font-size: var(--fs-3xl);
  }
}
</style>
