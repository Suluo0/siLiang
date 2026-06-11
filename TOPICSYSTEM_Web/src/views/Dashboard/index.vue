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
  padding: 0;
  max-width: 1400px;
  margin: 0 auto;
}
.content-grid {
  display: grid;
  grid-template-columns: 300px 1fr 280px;
  gap: 24px;
}
@media (max-width: 1200px) { .content-grid { grid-template-columns: 1fr 280px; } }
@media (max-width: 1024px) { .content-grid { grid-template-columns: 1fr; } }
</style>
