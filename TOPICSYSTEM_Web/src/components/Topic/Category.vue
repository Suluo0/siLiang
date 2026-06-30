<template>
  <!-- 可复用的「分类纵向列」组件:题库页 3 列复用它,后续其他页面也可复用 -->
  <div class="feed-col">
    <div class="col-header">
      <span class="col-dot" :style="{ background: color }"></span>
      {{ label }}
      <span class="col-count">{{ items.length }}</span>
    </div>

    <div class="col-body">
      <div v-if="!items.length" class="col-empty">{{ emptyText }}</div>
      <div
        v-for="item in items" :key="item.id"
        class="card" @click="$emit('card-click', item.id)">
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
</template>

<script setup>
defineProps({
  label: { type: String, default: '' },
  color: { type: String, default: '#6366f1' },
  items: { type: Array, default: () => [] },
  emptyText: { type: String, default: '暂无' },
})
defineEmits(['card-click'])
</script>

<style scoped>
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

/* ─── 响应式:移动端列内调整 ─── */
@media (max-width: 767px) {
  .feed-col {
    padding: 14px 12px 6px;
    min-height: 0;
    max-width: 100%;
    box-sizing: border-box;
  }
  /* 移动端每个分类区不再各自滚动,跟随整页滚动 */
  .col-body {
    overflow-y: visible;
    flex: none;
    padding-right: 0;
  }
  .card {
    padding: 14px 14px;
    max-width: 100%;
    box-sizing: border-box;
  }
  .card-title { font-size: 14px; }
}
</style>
