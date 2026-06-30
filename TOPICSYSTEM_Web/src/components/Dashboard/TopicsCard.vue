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
  gap: var(--sp-3);
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--fs-xl);
  font-weight: var(--fw-semibold);
  color: var(--text-1);
  margin: 0;
  min-width: 0;
}

.card-title svg {
  color: var(--color-primary);
  flex-shrink: 0;
}

.card-more {
  font-size: var(--fs-md);
  color: var(--color-primary);
  text-decoration: none;
  white-space: nowrap;
}

.topic-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.topic-item {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-3);
  border-radius: var(--r-lg);
  transition: background var(--duration-fast);
  min-width: 0;
}

.topic-item:hover {
  background: var(--bg-soft-2);
}

.topic-rank {
  flex: 0 0 auto;
  width: 28px;
  height: 28px;
  border-radius: var(--r-sm);
  background: var(--bg-tag);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fs-md);
  font-weight: var(--fw-semibold);
  color: var(--text-4);
}

.topic-rank.top {
  background: var(--gradient-brand);
  color: #fff;
}

.topic-info {
  flex: 1;
  min-width: 0;
}

.topic-name {
  font-size: var(--fs-md);
  font-weight: var(--fw-medium);
  color: var(--text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topic-meta {
  font-size: var(--fs-xs);
  color: var(--text-4);
  margin-top: 4px;
}

.dot {
  margin: 0 4px;
}

.topic-progress {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-shrink: 0;
}

.progress-bar {
  width: 60px;
  height: 4px;
  background: var(--border-light);
  border-radius: 2px;
}

.progress-fill {
  height: 100%;
  background: var(--gradient-brand);
  border-radius: 2px;
}

.progress-text {
  font-size: var(--fs-xs);
  color: var(--text-4);
  min-width: 32px;
}

/* 移动端:进度条窄屏隐藏文字保留色条 */
@media (max-width: 767px) {
  .content-card {
    padding: var(--sp-4);
    border-radius: var(--r-lg);
  }
  .topic-progress {
    gap: var(--sp-1);
  }
  .progress-bar {
    width: 40px;
  }
  .progress-text {
    display: none;
  }
}
</style>
