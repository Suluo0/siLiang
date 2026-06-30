<template>
  <div class="mastery-panel">
    <!-- 作答区 -->
    <div class="answer-block">
      <div class="answer-head">
        <span class="answer-title">默写/复述你的答案</span>
        <el-button
          v-if="lastResult || attempts.length"
          text size="small" @click="showHistory = !showHistory"
        >{{ showHistory ? '收起记录' : `历史记录 (${attempts.length})` }}</el-button>
      </div>
      <el-input
        v-model="answer"
        type="textarea"
        :rows="5"
        :maxlength="2000"
        show-word-limit
        placeholder="凭记忆写出你对该知识点的理解（≥10 字）。系统会对照标准答案从三个维度打分。"
      />
      <div class="answer-actions">
        <span class="hint" :class="{ warn: answer.trim().length > 0 && answer.trim().length < 10 }">
          {{ answer.trim().length < 10 ? `还需 ${10 - answer.trim().length} 字` : `${answer.trim().length} 字` }}
        </span>
        <div class="btn-row">
          <el-button
            size="small" @click="markMastered" :loading="marking"
          >我已掌握（跳过自查）</el-button>
          <el-button
            type="primary" size="small"
            :disabled="answer.trim().length < 10" :loading="checking"
            @click="submit"
          >提交评分</el-button>
        </div>
      </div>
    </div>

    <!-- 评分结果 -->
    <transition name="fade">
      <div v-if="lastResult" class="result-block">
        <div class="result-head">
          <div class="total-score" :class="lastResult.mastered ? 'ok' : 'no'">
            <span class="score-num">{{ Math.round(lastResult.total * 100) }}</span>
            <span class="score-unit">分</span>
          </div>
          <div class="result-verdict">
            <el-tag :type="lastResult.mastered ? 'success' : 'warning'" effect="light" size="small">
              {{ lastResult.mastered ? '✓ 已达标' : '继续努力' }}
            </el-tag>
            <p class="feedback">{{ lastResult.feedback }}</p>
          </div>
        </div>
        <!-- 三维横条 -->
        <div class="dims">
          <div v-for="d in dimRows(lastResult.scores)" :key="d.key" class="dim">
            <span class="dim-label">{{ d.label }}</span>
            <el-progress
              :percentage="Math.round(d.value * 100)"
              :stroke-width="8"
              :color="d.color"
              class="dim-bar"
            />
          </div>
        </div>
      </div>
    </transition>

    <!-- 历史记录 -->
    <transition name="fade">
      <div v-if="showHistory && attempts.length" class="history-block">
        <div v-for="a in attempts" :key="a.id" class="history-item">
          <div class="hi-head">
            <el-tag :type="a.is_mastered ? 'success' : 'info'" size="small" effect="plain">
              {{ Math.round(a.total * 100) }} 分
            </el-tag>
            <span class="hi-time">第 {{ a.attempt_number }} 次 · {{ fmtTime(a.created_at) }}</span>
          </div>
          <p class="hi-answer">{{ a.answer_text }}</p>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { masteryCheck, setTopicStatus, getMasteryAttempts } from '@/api/topic'

const props = defineProps({
  topicId: { type: [String, Number], required: true },
})
const emit = defineEmits(['mastered', 'status-change'])

const answer = ref('')
const checking = ref(false)
const marking = ref(false)
const lastResult = ref(null)
const attempts = ref([])
const showHistory = ref(false)

const DIMS = [
  { key: 'keypoint', label: '要点覆盖', color: '#6366f1' },
  { key: 'keyword', label: '关键词', color: '#10b981' },
  { key: 'structure', label: '结构完整', color: '#f59e0b' },
]
function dimRows(scores) {
  if (!scores) return []
  return DIMS.map(d => ({ ...d, value: scores[d.key] ?? 0 }))
}

function fmtTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function loadAttempts() {
  try {
    const res = await getMasteryAttempts(props.topicId)
    attempts.value = res.attempts || []
  } catch { /* 未登录或无记录，静默 */ }
}

async function submit() {
  if (answer.value.trim().length < 10) return
  checking.value = true
  try {
    const res = await masteryCheck(props.topicId, answer.value.trim())
    lastResult.value = res
    if (res.mastered) {
      ElMessage.success('达标！已记入掌握')
      emit('mastered', props.topicId)
    }
    emit('status-change')
    await loadAttempts()
  } catch (e) {
    // request.js 已弹错误提示
  } finally {
    checking.value = false
  }
}

async function markMastered() {
  marking.value = true
  try {
    await setTopicStatus(props.topicId, 'mastered')
    ElMessage.success('已标记为掌握')
    emit('mastered', props.topicId)
    emit('status-change')
  } catch (e) {
    // request.js 已弹错误提示
  } finally {
    marking.value = false
  }
}

onMounted(loadAttempts)
</script>

<style scoped>
.mastery-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 4px;
}

/* ── 作答 ── */
.answer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.answer-title { font-size: 14px; font-weight: 600; color: #1a1a2e; }
.answer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  gap: 12px;
}
.hint { font-size: 12px; color: #999; }
.hint.warn { color: #f59e0b; }
.btn-row { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }

/* ── 结果 ── */
.result-block {
  background: #f8f9fc;
  border-radius: 12px;
  padding: 16px;
}
.result-head {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 14px;
}
.total-score {
  flex-shrink: 0;
  display: flex;
  align-items: baseline;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  font-weight: 800;
}
.total-score.ok { background: rgba(16,185,129,0.12); color: #10b981; }
.total-score.no { background: rgba(245,158,11,0.12); color: #f59e0b; }
.score-num { font-size: 26px; line-height: 1; }
.score-unit { font-size: 12px; margin-left: 1px; }
.result-verdict { flex: 1; min-width: 0; }
.feedback { margin: 6px 0 0; font-size: 13px; color: #555; line-height: 1.5; }

/* ── 五维横条 ── */
.dims { display: flex; flex-direction: column; gap: 8px; }
.dim { display: flex; align-items: center; gap: 10px; }
.dim-label {
  flex-shrink: 0; width: 60px;
  font-size: 12px; color: #666; text-align: right;
}
.dim-bar { flex: 1; }

/* ── 历史 ── */
.history-block {
  display: flex; flex-direction: column; gap: 10px;
  border-top: 1px dashed #eee; padding-top: 12px;
}
.history-item { background: #fafafa; border-radius: 8px; padding: 10px 12px; }
.hi-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.hi-time { font-size: 12px; color: #999; }
.hi-answer {
  margin: 0; font-size: 13px; color: #666; line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── 移动端 ── */
@media (max-width: 767px) {
  .btn-row { width: 100%; }
  .answer-actions { flex-direction: column; align-items: stretch; }
  .hint { order: 2; text-align: right; }
}
</style>
