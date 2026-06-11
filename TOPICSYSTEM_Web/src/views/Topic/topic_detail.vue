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

      <section class="section" v-if="detail.detailed_explanation">
        <h2 class="section-title">详细解释</h2>
        <div class="text" v-html="formatText(detail.detailed_explanation)"></div>
      </section>

      <section class="section" v-if="detail.code_example">
        <h2 class="section-title">代码示例</h2>
        <pre class="code-block"><code>{{ handleNewline(detail.code_example) }}</code></pre>
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

      <section class="section" v-if="detail.traps">
        <h2 class="section-title">常见陷阱</h2>
        <p class="text" v-html="formatText(detail.traps)"></p>
      </section>

      <section class="section" v-if="detail.bonuses">
        <h2 class="section-title">加分项</h2>
        <p class="text" v-html="formatText(detail.bonuses)"></p>
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
    </div>

    <div v-if="!loading && !detail" class="empty-state">
      <el-empty description="未找到该面试题" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getTopicDetail } from '@/api/topic'

const router = useRouter()
const route = useRoute()

const detail = ref(null)
const loading = ref(false)

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
</style>