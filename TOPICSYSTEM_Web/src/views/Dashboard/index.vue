<template>
  <div class="dashboard">
    <HeroSection />
    <StatsSection @stats-loaded="onStatsLoaded" />
    <section class="content-grid">
      <TopicsCard />
      <FeedCard />
      <ProgressCard />
    </section>

    <!-- 偏好弹窗 -->
    <PreferencesModal v-if="showPrefsModal" :show="showPrefsModal" @done="showPrefsModal = false" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import HeroSection from '@/components/Dashboard/HeroSection.vue'
import StatsSection from '@/components/Dashboard/StatsSection.vue'
import TopicsCard from '@/components/Dashboard/TopicsCard.vue'
import FeedCard from '@/components/Dashboard/FeedCard.vue'
import ProgressCard from '@/components/Dashboard/ProgressCard.vue'
import PreferencesModal from '@/components/Dashboard/PreferencesModal.vue'

const showPrefsModal = ref(false)

function onStatsLoaded(data) {
  if (!data || !data.auth) return   // 未登录不弹
  if (data.pref) return
  if (localStorage.getItem('skip_prefs_modal') === 'true') return
  showPrefsModal.value = true
}
</script>

<style scoped>
.dashboard {
  width: 100%;
  max-width: var(--container-xl);  /* 1400 */
  margin: 0 auto;
  padding: 0;
  /* 防止子内容意外溢出 */
  min-width: 0;
}

/* ──────────────────────────────────────
 * 三栏布局
 *   ≥ xl (1280): 280 / 1fr / 280
 *   ≥ lg (1024): 1fr / 280       (隐藏左栏 TopicsCard 不行,改成 1fr 1fr 上下叠 ProgressCard 折叠到底部)
 *   ≥ md (768):  两列(主内容 + 侧栏堆叠)
 *   <  md       : 单栏
 *
 * 简化策略:
 *   ≥ xl   三栏并排
 *   md~xl  上下堆叠,但 FeedCard 占满,Topics + Progress 并排两列
 *   <  md  全部单列
 * ──────────────────────────────────────*/

.content-grid {
  display: grid;
  gap: var(--sp-6);
  /* 默认(< md): 单列 */
  grid-template-columns: 1fr;
  /* 让子项不会被自身 min-content 撑开 */
  grid-auto-rows: min-content;
}

.content-grid > * {
  min-width: 0;  /* 关键:防止 grid item 被子内容撑爆 */
}

/* ≥ md 平板:2 列,FeedCard 跨整行 */
@media (min-width: 768px) {
  .content-grid {
    grid-template-columns: 1fr 1fr;
    grid-template-areas:
      "feed feed"
      "topics progress";
  }
  .content-grid > :nth-child(1) { grid-area: topics; }   /* TopicsCard */
  .content-grid > :nth-child(2) { grid-area: feed; }     /* FeedCard */
  .content-grid > :nth-child(3) { grid-area: progress; } /* ProgressCard */
}

/* ≥ xl 桌面:三栏并排 */
@media (min-width: 1280px) {
  .content-grid {
    grid-template-columns: 300px 1fr 300px;
    grid-template-areas: "topics feed progress";
  }
}
</style>
