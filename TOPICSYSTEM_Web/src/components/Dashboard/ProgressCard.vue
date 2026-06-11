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
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.card-title svg {
  color: #667eea;
}

.progress-overview {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

.progress-ring {
  position: relative;
  width: 140px;
  height: 140px;
}

.progress-ring svg {
  transform: rotate(-90deg);
}

.ring-bg {
  fill: none;
  stroke: #f0f2f5;
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
  font-size: 32px;
  font-weight: 700;
  color: #1a1a2e;
}

.ring-label {
  font-size: 12px;
  color: #86909c;
}

.progress-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.progress-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.progress-info {
  flex: 1;
}

.progress-name {
  font-size: 14px;
  color: #1a1a2e;
  margin-bottom: 6px;
  display: block;
}

.progress-bar-small {
  width: 100%;
  height: 6px;
  background: #f0f2f5;
  border-radius: 3px;
}

.progress-fill-small {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 3px;
}

.progress-percent {
  font-size: 14px;
  font-weight: 600;
  color: #667eea;
}
</style>
