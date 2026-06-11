<template>
  <div class="topic-detail" v-loading="loading">
    <div class="back-btn">
      <el-button @click="goBack" text>
        <el-icon><ArrowLeft /></el-icon>
        返回题库
      </el-button>
    </div>

    <div class="content" v-if="detail">
      <header class="header">
        <h1 class="title">{{ detail.topic }}</h1>
        <div class="meta">
          <el-tag type="info">{{ detail.domain }}</el-tag>
          <el-tag v-if="detail.category">{{ detail.category }}</el-tag>
          <span class="difficulty">难度 {{ detail.difficulty }}</span>
        </div>
      </header>

      <section class="section" v-if="detail.core_summary">
        <h2 class="section-title">核心概述</h2>
        <p class="text" v-html="formatText(detail.core_summary)"></p>
      </section>

      <section class="section" v-if="detail.core_points">
        <h2 class="section-title">核心要点</h2>
        <div class="text" v-html="formatText(detail.core_points)"></div>
      </section>

      <section class="section" v-if="detail.prerequisites?.length">
        <h2 class="section-title">前置知识</h2>
        <ul class="list">
          <li v-for="(item, index) in detail.prerequisites" :key="index">
            {{ item.content }}
          </li>
        </ul>
      </section>

      <section class="section" v-if="detail.core_concepts?.length">
        <h2 class="section-title">核心概念</h2>
        <ul class="list">
          <li v-for="(item, index) in detail.core_concepts" :key="index">
            {{ item.content }}
          </li>
        </ul>
      </section>

      <!-- 主内容 -->
      <section class="section" v-if="detail.detailed_explanation || isLocked('detailed_explanation')">
        <h2 class="section-title">详细解释</h2>
        <div class="locked-wrap" :class="{ masked: isLocked('detailed_explanation') }">
          <div class="text" v-html="formatText(detail.detailed_explanation || '')" v-if="detail.detailed_explanation"></div>
        </div>
      </section>

      <section class="section" v-if="detail.code_example || isLocked('code_example')">
        <h2 class="section-title">代码示例</h2>
        <div class="locked-wrap" :class="{ masked: isLocked('code_example') }">
          <pre class="code-block" v-if="detail.code_example"><code>{{ handleNewline(detail.code_example) }}</code></pre>
        </div>
      </section>

      <section class="section" v-if="detail.similar_questions?.length">
        <h2 class="section-title">相似题目</h2>
        <ul class="list">
          <li v-for="(item, index) in detail.similar_questions" :key="index">
            {{ item.question }}
          </li>
        </ul>
      </section>

      <section class="section" v-if="detail.advanced_questions?.length">
        <h2 class="section-title">进阶题目</h2>
        <ul class="list">
          <li v-for="(item, index) in detail.advanced_questions" :key="index">
            {{ item.question }}
          </li>
        </ul>
      </section>

      <section class="section" v-if="detail.traps || isLocked('traps')">
        <h2 class="section-title">常见陷阱</h2>
        <div class="locked-wrap" :class="{ masked: isLocked('traps') }">
          <p class="text" v-html="formatText(detail.traps || '')" v-if="detail.traps"></p>
        </div>
      </section>

      <section class="section" v-if="detail.bonuses || isLocked('bonuses')">
        <h2 class="section-title">加分项</h2>
        <div class="locked-wrap" :class="{ masked: isLocked('bonuses') }">
          <p class="text" v-html="formatText(detail.bonuses || '')" v-if="detail.bonuses"></p>
        </div>
      </section>

      <section class="section" v-if="detail.derivatives?.length">
        <h2 class="section-title">衍生知识</h2>
        <ul class="list">
          <li v-for="(item, index) in detail.derivatives" :key="index">
            {{ item.content }}
          </li>
        </ul>
      </section>

      <section class="section" v-if="detail.extensions?.length">
        <h2 class="section-title">扩展内容</h2>
        <ul class="list">
          <li v-for="(item, index) in detail.extensions" :key="index">
            {{ item.content }}
          </li>
        </ul>
      </section>

      <section class="section" v-if="detail.references?.length">
        <h2 class="section-title">参考资料</h2>
        <ul class="references">
          <li v-for="(item, index) in detail.references" :key="index">
            <a :href="item.url" target="_blank" v-if="item.url">{{ item.title }}</a>
            <span v-else>{{ item.title }}</span>
            <p v-if="item.description" class="ref-desc">{{ item.description }}</p>
          </li>
        </ul>
      </section>

      <!-- 统一锁 Banner -->
      <div class="lock-bar" v-if="detail.locked">
        <div class="lock-banner" @click="showUpgrade = true">
          <el-icon><Lock /></el-icon>
          <span>您的试用次数已耗尽 · 点击了解会员</span>
        </div>
      </div>
    </div>

    <div v-if="!loading && !detail" class="empty-state">
      <el-empty description="未找到该面试题" />
    </div>

    <!-- 会员升级 Modal -->
    <el-dialog v-model="showUpgrade" title="" width="720px" :close-on-click-modal="false" class="upgrade-dialog">
      <div class="upgrade-hero">
        <div class="hero-badge">限时特惠</div>
        <h2 class="hero-title">解锁完整题库</h2>
        <p class="hero-sub">选择适合你的方案，提升面试备战效率</p>
      </div>

      <div class="plan-grid">
        <!-- 免费版 -->
        <div class="plan-card free">
          <div class="plan-head">免费版</div>
          <div class="plan-price">¥0<span>/月</span></div>
          <ul class="plan-features">
            <li><span class="check muted">✓</span> 面试题库浏览</li>
            <li><span class="check muted">✓</span> 核心概述 + 核心要点</li>
            <li><span class="check muted">✓</span> 20 次详细内容访问</li>
            <li><span class="cross">✕</span> Agent 对话 5 次</li>
            <li><span class="cross">✕</span> 代码示例查看</li>
            <li><span class="cross">✕</span> 模拟面试功能</li>
            <li><span class="cross">✕</span> 优先获取新题</li>
          </ul>
          <div class="plan-btn outline">当前方案</div>
        </div>

        <!-- 高级版 -->
        <div class="plan-card premium">
          <div class="plan-ribbon">🔥 推荐</div>
          <div class="plan-head">高级会员</div>
          <div class="plan-price">¥29<span>/月</span></div>
          <div class="plan-saving">省 ¥9/月 · 年付 ¥199</div>
          <ul class="plan-features">
            <li><span class="check glow">✓</span> 面试题库无限浏览</li>
            <li><span class="check glow">✓</span> 完整详细解释</li>
            <li><span class="check glow">✓</span> 所有代码示例</li>
            <li><span class="check glow">✓</span> Agent 对话 200 次/月</li>
            <li><span class="check glow">✓</span> AI 模拟面试</li>
            <li><span class="check glow">✓</span> 常见陷阱 + 加分项</li>
            <li><span class="check glow">✓</span> 优先获取新题</li>
          </ul>
          <div class="plan-btn gradient">立即升级</div>
        </div>
      </div>

      <div class="upgrade-footer">
        <el-button text @click="showUpgrade = false">暂不需要，继续试用</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Lock } from '@element-plus/icons-vue'
import { getTopicDetail } from '@/api/topic'

const router = useRouter()
const route = useRoute()

const detail = ref(null)
const loading = ref(false)
const showUpgrade = ref(false)

const fetchDetail = async () => {
  loading.value = true
  try {
    const res = await getTopicDetail(route.params.id)
    detail.value = res
  } catch (error) {
    console.error('获取详情失败', error)
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push('/topic/library')
}

const isLocked = (section) => {
  return detail.value?.locked && detail.value?.locked_sections?.includes(section)
}

const formatText = (text) => {
  if (!text) return ''
  return text.replace(/\n/g, '<br>')
}

onMounted(() => {
  fetchDetail()
})

const handleNewline = (code) => {
  if (!code) return ''
  // 将字符串字面量 "\n" 替换为真正的换行符
  // 注意：这里需要匹配 "\\n"
  return code.replace(/\\n/g, '\n')
}
</script>

<style scoped>
.topic-detail {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 20px;
}

.back-btn {
  margin-bottom: 24px;
}

.content {
  background: #fff;
  border-radius: 12px;
  padding: 32px;
}

.header {
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid #f1f2f3;
}

.title {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 16px 0;
}

.meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.difficulty {
  font-size: 14px;
  color: #8a8a8a;
}

.section {
  margin-bottom: 32px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 16px 0;
}

.text {
  font-size: 15px;
  line-height: 1.8;
  color: #4a4a4a;
  white-space: pre-wrap;
}

.list {
  margin: 0;
  padding-left: 24px;
}

.list li {
  font-size: 15px;
  line-height: 1.8;
  color: #4a4a4a;
  margin-bottom: 8px;
}

.code-block {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 20px 24px;
  margin: 0;
  overflow: auto; /* 保持滚动条 */
  max-height: 600px;
  /* 移除这里的 white-space: pre; */
}

.code-block code {
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #d4d4d4;
  
  /* 添加以下属性 */
  display: block;        /* 强制作为块级元素，占据完整宽度 */
  white-space: pre;      /* 核心：严格保留换行符 */
  text-align: left;      /* 防止意外的居中 */
}

.references {
  margin: 0;
  padding-left: 24px;
}

.references li {
  margin-bottom: 12px;
}

.references a {
  color: #0070f3;
  text-decoration: none;
}

.references a:hover {
  text-decoration: underline;
}

.ref-desc {
  font-size: 13px;
  color: #8a8a8a;
  margin: 4px 0 0 0;
}

.empty-state {
  padding: 60px 0;
}

/* ── 锁定蒙版 ── */
.locked-wrap { position: relative; }
.locked-wrap.masked { max-height: 200px; overflow: hidden; }
.locked-wrap.masked::after {
  content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 80px;
  background: linear-gradient(transparent, #fff);
  z-index: 1;
}
.lock-bar {
  padding: 32px 0 16px;
  display: flex; justify-content: center;
}
.lock-banner {
  background: rgba(99, 102, 241, 0.92); color: #fff;
  padding: 10px 28px; border-radius: 10px; font-size: 14px; font-weight: 600;
  display: flex; align-items: center; gap: 8px;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3);
  cursor: pointer;
}
.lock-banner:hover { background: rgba(99, 102, 241, 1); }

/* ── 会员升级 Modal ── */
.upgrade-dialog :deep(.el-dialog__header) { display: none; }
.upgrade-dialog :deep(.el-dialog__body) { padding: 0; }

.upgrade-hero {
  text-align: center; padding: 32px 24px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff; border-radius: 12px 12px 0 0; margin: -1px;
}
.hero-badge {
  display: inline-block; background: rgba(255,255,255,.2); color: #fff;
  font-size: 12px; padding: 3px 14px; border-radius: 20px; margin-bottom: 12px;
}
.hero-title { font-size: 24px; font-weight: 800; margin: 0 0 6px; }
.hero-sub { font-size: 14px; opacity: .85; margin: 0; }

.plan-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
  padding: 24px 32px 16px;
}
.plan-card {
  border-radius: 14px; padding: 24px 20px 20px; position: relative;
  border: 2px solid #e8e8e8; text-align: center;
}
.plan-card.premium {
  border-color: #667eea; background: #fafaff;
  box-shadow: 0 8px 30px rgba(102,126,234,.15);
  transform: scale(1.03);
}
.plan-ribbon {
  position: absolute; top: -12px; right: 16px;
  background: linear-gradient(135deg, #f59e0b, #f97316); color: #fff;
  font-size: 12px; font-weight: 700; padding: 4px 14px; border-radius: 8px;
}
.plan-head { font-size: 16px; font-weight: 700; color: #333; margin-bottom: 8px; }
.plan-price { font-size: 36px; font-weight: 800; color: #1a1a2e; }
.plan-price span { font-size: 14px; font-weight: 400; color: #999; }
.premium .plan-price { color: #667eea; }
.plan-saving { font-size: 12px; color: #f59e0b; margin: 4px 0 14px; font-weight: 500; }
.plan-features {
  list-style: none; padding: 0; margin: 0 0 16px; text-align: left;
}
.plan-features li { font-size: 13px; color: #555; padding: 6px 0; display: flex; align-items: center; gap: 8px; }
.check { color: #10b981; font-weight: 700; }
.check.muted { color: #ccc; }
.check.glow { color: #667eea; text-shadow: 0 0 6px rgba(102,126,234,.3); }
.cross { color: #ddd; font-weight: 700; }
.plan-btn {
  padding: 10px 0; border-radius: 10px; font-size: 14px; font-weight: 600;
}
.plan-btn.outline { border: 2px solid #ddd; color: #999; }
.plan-btn.gradient {
  background: linear-gradient(135deg, #667eea, #764ba2); color: #fff;
  box-shadow: 0 4px 14px rgba(102,126,234,.4); cursor: pointer;
}
.plan-btn.gradient:hover { opacity: .9; }
.upgrade-footer { text-align: center; padding: 0 0 20px; }

.lock-banner { cursor: pointer; transition: all .2s; }
.lock-banner:hover { transform: translateY(-1px); }
</style>