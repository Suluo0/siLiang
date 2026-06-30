<template>
  <section class="hero-section">
    <div class="hero-content">
      <h1 class="hero-title">
        <span class="gradient-text">思量</span>
        <br />现在开始吧,打算学点什么?
      </h1>
      <p class="hero-subtitle">
        付思量,自难忘
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
/* ════════════════════════════════════════════
 * Hero 主视觉
 *   桌面:左文右图,padding 60/40
 *   平板:左文右图(图缩小)
 *   手机:仅文字居中,藏图,padding 大幅收缩
 * ════════════════════════════════════════════ */

.hero-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  /* clamp 流式 padding,720 视口 ~32px,1280 视口 ~60px */
  padding: clamp(28px, 4.5vw, 60px) clamp(20px, 3.5vw, 48px);
  background: var(--gradient-brand);
  border-radius: var(--r-2xl);
  margin-bottom: var(--sp-7);
  position: relative;
  overflow: hidden;
  gap: var(--sp-6);
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
  pointer-events: none;
}

.hero-content {
  flex: 1 1 auto;
  z-index: 1;
  min-width: 0;
}

.hero-title {
  /* 桌面 ~44, 笔记本 ~36, 平板 ~30, 手机 ~22 */
  font-size: clamp(22px, 4.2vw, 48px);
  font-weight: var(--fw-bold);
  color: #fff;
  line-height: var(--lh-tight);
  margin: 0 0 var(--sp-4);
  /* 避免极小屏长字符撑爆 */
  word-break: break-word;
}

.gradient-text {
  background: linear-gradient(90deg, #fff 0%, #e0c3fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: var(--fs-xl);   /* clamp 16~18 */
  color: rgba(255, 255, 255, 0.85);
  margin: 0 0 var(--sp-7);
  max-width: 400px;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-3);
}

.btn-primary,
.btn-secondary {
  height: var(--btn-h-lg);
  padding: 0 var(--sp-6);
  border-radius: var(--r-lg);
  font-size: var(--fs-lg);
  font-weight: var(--fw-semibold);
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-2);
  white-space: nowrap;
}

.btn-primary {
  background: #fff;
  color: var(--color-primary);
  border: none;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-hover);
}

.btn-secondary {
  background: transparent;
  color: #fff;
  border: 2px solid rgba(255, 255, 255, 0.5);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: #fff;
}

/* ─── 右侧轨道动画区 ─── */

.hero-visual {
  flex: 0 0 auto;
  display: flex;
  justify-content: center;
  align-items: center;
}

.orbit-container {
  position: relative;
  /* 流式尺寸:平板缩到 240,桌面 320 */
  width: clamp(220px, 22vw, 320px);
  height: clamp(220px, 22vw, 320px);
}

.orbit {
  position: absolute;
  border: 1px dashed rgba(255, 255, 255, 0.15);
  border-radius: 50%;
  animation: rotate 20s linear infinite;
}

.orbit-1 { width: 100%; height: 100%; top: 0; left: 0; }
.orbit-2 { width: 75%; height: 75%; top: 12.5%; left: 12.5%; animation-duration: 15s; animation-direction: reverse; }
.orbit-3 { width: 50%; height: 50%; top: 25%; left: 25%; animation-duration: 10s; }

@keyframes rotate {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

.center-node {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 100px;
  height: 100px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.globe {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--gradient-brand);
  position: relative;
  box-shadow:
    inset -10px -10px 20px rgba(0, 0, 0, 0.2),
    inset 10px 10px 20px rgba(255, 255, 255, 0.1),
    0 0 40px rgba(99, 102, 241, 0.5);
  animation: globe-spin 8s linear infinite;
  overflow: hidden;
}

.globe-surface {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: linear-gradient(135deg, transparent 0%, rgba(255,255,255,0.2) 50%, transparent 100%);
}

.globe-grid {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background:
    repeating-linear-gradient(0deg, transparent, transparent 8px, rgba(255,255,255,0.1) 8px, rgba(255,255,255,0.1) 9px),
    repeating-linear-gradient(90deg, transparent, transparent 8px, rgba(255,255,255,0.1) 8px, rgba(255,255,255,0.1) 9px);
  animation: globe-grid-spin 12s linear infinite reverse;
}

@keyframes globe-spin     { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes globe-grid-spin{ from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.satellite {
  position: absolute;
  top: 50%; left: 50%;
  transform-origin: center;
}
.satellite-1 { animation: orbit-1 6s linear infinite; }
.satellite-2 { animation: orbit-2 8s linear infinite; }
.satellite-3 { animation: orbit-3 10s linear infinite; }

.satellite-ball {
  width: 16px; height: 16px;
  border-radius: 50%;
  background: linear-gradient(135deg, #fff 0%, #e0c3fc 100%);
  box-shadow: 0 0 15px rgba(255,255,255,0.6);
  transform: translate(-50%, -50%);
  animation: ball-pulse 2s ease-in-out infinite;
}
.ball-2 { width: 12px; height: 12px; background: linear-gradient(135deg, #ffd700, #ff6b6b); box-shadow: 0 0 12px rgba(255,215,0,0.6); }
.ball-3 { width: 10px; height: 10px; background: linear-gradient(135deg, #00d4ff, #6366f1); box-shadow: 0 0 10px rgba(0,212,255,0.6); }

@keyframes orbit-1 {
  from { transform: translate(-50%, -50%) rotate(0deg)   translateX(140px) rotate(0deg); }
  to   { transform: translate(-50%, -50%) rotate(360deg) translateX(140px) rotate(-360deg); }
}
@keyframes orbit-2 {
  from { transform: translate(-50%, -50%) rotate(120deg) translateX(115px) rotate(-120deg); }
  to   { transform: translate(-50%, -50%) rotate(480deg) translateX(115px) rotate(-480deg); }
}
@keyframes orbit-3 {
  from { transform: translate(-50%, -50%) rotate(240deg) translateX(80px)  rotate(-240deg); }
  to   { transform: translate(-50%, -50%) rotate(600deg) translateX(80px)  rotate(-600deg); }
}
@keyframes ball-pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); }
  50%      { transform: translate(-50%, -50%) scale(1.2); }
}

/* ─── 响应式 ─── */

/* < lg 笔记本以下:文字居中,图片缩小 */
@media (max-width: 1023px) {
  .hero-section {
    flex-direction: column;
    text-align: center;
    align-items: center;
  }
  .hero-subtitle {
    max-width: 100%;
  }
  .hero-actions {
    justify-content: center;
  }
}

/* < md 手机:藏掉装饰图,留更多空间给文案 */
@media (max-width: 767px) {
  .hero-section {
    margin-bottom: var(--sp-5);
  }
  .hero-visual {
    display: none;
  }
  .hero-actions {
    width: 100%;
  }
  .btn-primary,
  .btn-secondary {
    flex: 1;
    min-width: 120px;
  }
}
</style>
