<template>
  <div class="content-card">
    <div class="card-header">
      <h2 class="card-title">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2L2 7l10 5 10-5-10-5z"/>
          <path d="M2 17l10 5 10-5"/>
          <path d="M2 12l10 5 10-5"/>
        </svg>
        热门面经
      </h2>
      <a href="#" class="card-more">查看全部</a>
    </div>
    <div class="topic-list">
      <div class="topic-item" v-for="topic in topics" :key="topic.id">
        <div class="topic-rank" :class="{ top: topic.rank <= 3 }">{{ topic.rank }}</div>
        <div class="topic-info">
          <div class="topic-name">{{ topic.name }}</div>
          <div class="topic-meta">
            <span>{{ topic.users }} 浏览</span>
            <span class="dot">·</span>
            <span>{{ topic.articles }} 评论</span>
          </div>
        </div>
        <div class="topic-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: topic.progress + '%' }"></div>
          </div>
          <span class="progress-text">{{ topic.progress }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const topics = ref([
  { id: 1, rank: 1, name: '字节跳动一面', users: '3.2k', articles: 89, progress: 92 },
  { id: 2, rank: 2, name: '阿里二面题库', users: '2.8k', articles: 76, progress: 85 },
  { id: 3, rank: 3, name: '腾讯技术面试', users: '2.5k', articles: 68, progress: 78 },
  { id: 4, rank: 4, name: '美团社招面经', users: '1.9k', articles: 54, progress: 65 },
  { id: 5, rank: 5, name: '京东校招面经', users: '1.6k', articles: 45, progress: 52 },
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

.card-more {
  font-size: 14px;
  color: #667eea;
  text-decoration: none;
}

.topic-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.topic-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  transition: background 0.2s;
}

.topic-item:hover {
  background: #f7f8fa;
}

.topic-rank {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: #86909c;
}

.topic-rank.top {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.topic-info {
  flex: 1;
  min-width: 0;
}

.topic-name {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a2e;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topic-meta {
  font-size: 12px;
  color: #86909c;
  margin-top: 4px;
}

.dot {
  margin: 0 4px;
}

.topic-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-bar {
  width: 60px;
  height: 4px;
  background: #e8e8e8;
  border-radius: 2px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 2px;
}

.progress-text {
  font-size: 12px;
  color: #86909c;
  min-width: 32px;
}
</style>
