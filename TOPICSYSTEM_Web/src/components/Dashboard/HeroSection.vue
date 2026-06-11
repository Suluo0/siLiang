<template>
  <section class="hero-section">
    <div class="hero-content">
      <h1 class="hero-title">
        <span class="gradient-text">拓扑客</span>
        <br />现在开始吧，打算学点什么？
      </h1>
      <p class="hero-subtitle">
        探索主题之间的关联，构建你的专属知识网络
      </p>
      <div class="hero-actions">
        <button class="btn-primary" @click="handleStart">
          <span>开始</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </button>
        <button class="btn-secondary">了解更多</button>
      </div>
    </div>
    <div class="hero-visual">
      <div class="orbit-container">
        <!-- 轨道 -->
        <div class="orbit orbit-1"></div>
        <div class="orbit orbit-2"></div>
        <div class="orbit orbit-3"></div>
        
        <!-- 中心球体 -->
        <div class="center-node">
          <div class="globe">
            <div class="globe-surface"></div>
            <div class="globe-grid"></div>
          </div>
        </div>
        
        <!-- 公转的小球 -->
        <div class="satellite satellite-1">
          <div class="satellite-ball"></div>
        </div>
        <div class="satellite satellite-2">
          <div class="satellite-ball ball-2"></div>
        </div>
        <div class="satellite satellite-3">
          <div class="satellite-ball ball-3"></div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const handleStart = () => {
  router.push('/chat')
}
</script>

<style scoped>
.hero-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 60px 40px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 24px;
  margin-bottom: 32px;
  position: relative;
  overflow: hidden;
}

.hero-section::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
  border-radius: 50%;
}

.hero-content {
  flex: 1;
  z-index: 1;
}

.hero-title {
  font-size: 48px;
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
  margin-bottom: 16px;
}

.gradient-text {
  background: linear-gradient(90deg, #fff 0%, #e0c3fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.85);
  margin-bottom: 32px;
  max-width: 400px;
}

.hero-actions {
  display: flex;
  gap: 16px;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 28px;
  background: #fff;
  color: #667eea;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
}

.btn-secondary {
  padding: 14px 28px;
  background: transparent;
  color: #fff;
  border: 2px solid rgba(255, 255, 255, 0.5);
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: #fff;
}

.hero-visual {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
}

.orbit-container {
  position: relative;
  width: 320px;
  height: 320px;
}

.orbit {
  position: absolute;
  border: 1px dashed rgba(255, 255, 255, 0.15);
  border-radius: 50%;
  animation: rotate 20s linear infinite;
}

.orbit-1 {
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
}

.orbit-2 {
  width: 75%;
  height: 75%;
  top: 12.5%;
  left: 12.5%;
  animation-duration: 15s;
  animation-direction: reverse;
}

.orbit-3 {
  width: 50%;
  height: 50%;
  top: 25%;
  left: 25%;
  animation-duration: 10s;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.center-node {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100px;
  height: 100px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 中心球体 */
.globe {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  box-shadow: 
    inset -10px -10px 20px rgba(0, 0, 0, 0.2),
    inset 10px 10px 20px rgba(255, 255, 255, 0.1),
    0 0 40px rgba(102, 126, 234, 0.5);
  animation: globe-spin 8s linear infinite;
  overflow: hidden;
}

.globe-surface {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: linear-gradient(
    135deg,
    transparent 0%,
    rgba(255, 255, 255, 0.2) 50%,
    transparent 100%
  );
}

.globe-grid {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: 
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 8px,
      rgba(255, 255, 255, 0.1) 8px,
      rgba(255, 255, 255, 0.1) 9px
    ),
    repeating-linear-gradient(
      90deg,
      transparent,
      transparent 8px,
      rgba(255, 255, 255, 0.1) 8px,
      rgba(255, 255, 255, 0.1) 9px
    );
  animation: globe-grid-spin 12s linear infinite reverse;
}

@keyframes globe-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes globe-grid-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 公转小球 */
.satellite {
  position: absolute;
  top: 50%;
  left: 50%;
  transform-origin: center;
}

.satellite-1 {
  animation: orbit-1 6s linear infinite;
}

.satellite-2 {
  animation: orbit-2 8s linear infinite;
}

.satellite-3 {
  animation: orbit-3 10s linear infinite;
}

.satellite-ball {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: linear-gradient(135deg, #fff 0%, #e0c3fc 100%);
  box-shadow: 0 0 15px rgba(255, 255, 255, 0.6);
  transform: translate(-50%, -50%);
  animation: ball-pulse 2s ease-in-out infinite;
}

.ball-2 {
  width: 12px;
  height: 12px;
  background: linear-gradient(135deg, #ffd700 0%, #ff6b6b 100%);
  box-shadow: 0 0 12px rgba(255, 215, 0, 0.6);
}

.ball-3 {
  width: 10px;
  height: 10px;
  background: linear-gradient(135deg, #00d4ff 0%, #667eea 100%);
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.6);
}

@keyframes orbit-1 {
  from { 
    transform: translate(-50%, -50%) rotate(0deg) translateX(140px) rotate(0deg);
  }
  to { 
    transform: translate(-50%, -50%) rotate(360deg) translateX(140px) rotate(-360deg);
  }
}

@keyframes orbit-2 {
  from { 
    transform: translate(-50%, -50%) rotate(120deg) translateX(115px) rotate(-120deg);
  }
  to { 
    transform: translate(-50%, -50%) rotate(480deg) translateX(115px) rotate(-480deg);
  }
}

@keyframes orbit-3 {
  from { 
    transform: translate(-50%, -50%) rotate(240deg) translateX(80px) rotate(-240deg);
  }
  to { 
    transform: translate(-50%, -50%) rotate(600deg) translateX(80px) rotate(-600deg);
  }
}

@keyframes ball-pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); }
  50% { transform: translate(-50%, -50%) scale(1.2); }
}

@media (max-width: 1024px) {
  .hero-section {
    flex-direction: column;
    text-align: center;
    padding: 40px 24px;
  }
  .hero-subtitle {
    max-width: 100%;
  }
  .hero-actions {
    justify-content: center;
  }
  .hero-visual {
    display: none;
  }
  .hero-title {
    font-size: 32px;
  }
}
</style>
