<template>
  <div class="content-card">
    <div class="card-header">
      <h2 class="card-title">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <path d="M3 9h18"/>
          <path d="M9 21V9"/>
        </svg>
        推荐学习
      </h2>
      <div class="tab-nav">
        <button class="tab-btn active">为你推荐</button>
        <button class="tab-btn">最新</button>
        <button class="tab-btn">热门</button>
      </div>
    </div>
    <div class="feed-list">
      <article class="feed-item" v-for="item in feedItems" :key="item.id">
        <div class="feed-content">
          <div class="feed-tag" :style="{ background: item.tagColor }">{{ item.tag }}</div>
          <h3 class="feed-title">{{ item.title }}</h3>
          <p class="feed-excerpt">{{ item.excerpt }}</p>
          <div class="feed-meta">
            <div class="feed-author">
              <el-avatar :size="24" :src="item.avatar" />
              <span>{{ item.author }}</span>
            </div>
            <div class="feed-stats">
              <span><el-icon><View /></el-icon> {{ item.views }}</span>
              <span><el-icon><Star /></el-icon> {{ item.likes }}</span>
            </div>
          </div>
        </div>
        <div class="feed-cover" v-if="item.cover">
          <img :src="item.cover" :alt="item.title" />
        </div>
      </article>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { View, Star } from '@element-plus/icons-vue'

const feedItems = ref([
  {
    id: 1,
    tag: '前端',
    tagColor: 'rgba(64, 158, 255, 0.1)',
    title: 'Vue 3 Composition API 最佳实践指南',
    excerpt: '深入探索 Vue 3 Composition API 的核心概念和使用场景，帮助你构建更优雅的组件...',
    author: '技术小站',
    avatar: 'https://i.pravatar.cc/100?img=1',
    views: '2.3k',
    likes: 328,
    cover: 'https://picsum.photos/400/300?random=1'
  },
  {
    id: 2,
    tag: '后端',
    tagColor: 'rgba(103, 194, 58, 0.1)',
    title: 'FastAPI 高性能 Web 服务构建',
    excerpt: '利用 FastAPI 的异步特性，构建高性能 RESTful API 服务...',
    author: '编程之路',
    avatar: 'https://i.pravatar.cc/100?img=2',
    views: '1.8k',
    likes: 256,
    cover: 'https://picsum.photos/400/300?random=2'
  },
  {
    id: 3,
    tag: 'AI',
    tagColor: 'rgba(230, 162, 60, 0.1)',
    title: 'LangChain 入门：从零构建 AI 应用',
    excerpt: '使用 LangChain 框架快速构建基于大语言模型的应用程序...',
    author: 'AI 实验室',
    avatar: 'https://i.pravatar.cc/100?img=3',
    views: '3.1k',
    likes: 489,
    cover: 'https://picsum.photos/400/300?random=3'
  },
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
  flex-wrap: wrap;
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

.tab-nav {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.tab-btn {
  padding: 6px var(--sp-3);
  border: none;
  background: transparent;
  font-size: var(--fs-sm);
  color: var(--text-4);
  cursor: pointer;
  border-radius: var(--r-xs);
  transition: all var(--duration-fast);
}

.tab-btn.active {
  background: var(--color-primary);
  color: #fff;
}

.feed-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
}

.feed-item {
  display: flex;
  gap: var(--sp-5);
  padding: var(--sp-4);
  border-radius: var(--r-lg);
  transition: background var(--duration-fast);
  min-width: 0;
}

.feed-item:hover {
  background: var(--bg-soft-2);
}

.feed-content {
  flex: 1;
  min-width: 0;
}

.feed-tag {
  display: inline-block;
  padding: 4px var(--sp-3);
  border-radius: var(--r-xs);
  font-size: var(--fs-xs);
  font-weight: var(--fw-medium);
  margin-bottom: var(--sp-2);
}

.feed-title {
  font-size: var(--fs-lg);
  font-weight: var(--fw-semibold);
  color: var(--text-1);
  margin: 0 0 var(--sp-2);
  line-height: 1.4;
}

.feed-excerpt {
  font-size: var(--fs-md);
  color: var(--text-4);
  line-height: var(--lh-base);
  margin-bottom: var(--sp-3);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.feed-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.feed-author {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--fs-sm);
  color: var(--text-4);
  min-width: 0;
}

.feed-author span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.feed-stats {
  display: flex;
  gap: var(--sp-4);
  font-size: var(--fs-sm);
  color: var(--text-4);
  flex-shrink: 0;
}

.feed-stats span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.feed-cover {
  width: 140px;
  height: 100px;
  border-radius: var(--r-md);
  overflow: hidden;
  flex-shrink: 0;
}

.feed-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* ─── 响应式 ─── */

/* < md 手机:封面在上,内容在下;封面变高一些 */
@media (max-width: 767px) {
  .content-card {
    padding: var(--sp-4);
    border-radius: var(--r-lg);
  }
  .feed-item {
    flex-direction: column;
    gap: var(--sp-3);
    padding: var(--sp-3);
  }
  .feed-cover {
    order: -1;          /* 封面跑到顶部 */
    width: 100%;
    height: 160px;
    border-radius: var(--r-md);
  }
}
</style>
