<template>
  <div class="dashboard">
    <HeroSection />
    <StatsSection />
    <section class="content-grid">
      <TopicsCard />
      <FeedCard />
      <ProgressCard />
    </section>
  </div>
</template>

<script setup>
import HeroSection from '@/components/Dashboard/HeroSection.vue'
import StatsSection from '@/components/Dashboard/StatsSection.vue'
import TopicsCard from '@/components/Dashboard/TopicsCard.vue'
import FeedCard from '@/components/Dashboard/FeedCard.vue'
import ProgressCard from '@/components/Dashboard/ProgressCard.vue'
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

@media (max-width: 1200px) {
  .content-grid {
    grid-template-columns: 1fr 280px;
  }
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>
