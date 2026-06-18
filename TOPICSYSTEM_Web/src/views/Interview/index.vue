<template>
  <div class="interview-page">
    <!-- ═══ 阶段一：设置 ═══ -->
    <div v-if="phase === 'setup'" class="setup-container">
      <div class="setup-card">
        <div class="setup-header">
          <h2>模拟面试</h2>
          <p>配置面试参数，AI 面试官将根据你的简历和 JD 进行面试</p>
        </div>

        <el-form :model="form" label-position="top" class="setup-form">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="简历内容">
                <el-input
                  v-model="form.resume"
                  type="textarea"
                  :rows="8"
                  placeholder="粘贴你的简历文本..."
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="JD（岗位描述）">
                <el-input
                  v-model="form.jd"
                  type="textarea"
                  :rows="8"
                  placeholder="粘贴目标岗位的 JD 文本..."
                />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="面试官人设">
                <el-select v-model="form.persona_id" placeholder="选择面试官风格" class="full-width">
                  <el-option
                    v-for="p in personas"
                    :key="p.id"
                    :label="p.name"
                    :value="p.id"
                  >
                    <span>{{ p.name }}</span>
                    <span class="option-tag">{{ p.style }}</span>
                  </el-option>
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="最大轮次">
                <el-input-number v-model="form.max_rounds" :min="3" :max="20" :step="1" class="full-width" />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="技术深度">
                <el-tag effect="plain" type="info" class="depth-tag">
                  {{ personaDepth }}
                </el-tag>
              </el-form-item>
            </el-col>
          </el-row>

          <el-button type="primary" size="large" :loading="starting" @click="startInterview" class="start-btn">
            {{ starting ? '正在分析简历和JD...' : '开始面试' }}
          </el-button>
        </el-form>

        <!-- 分析结果 -->
        <div v-if="analysis" class="analysis-section">
          <el-divider>分析结果</el-divider>
          <el-row :gutter="16">
            <el-col :span="8">
              <div class="analysis-card">
                <div class="analysis-label">简历概览</div>
                <div class="analysis-value">{{ analysis.resume_analysis?.summary || '—' }}</div>
                <div class="analysis-detail" v-if="analysis.resume_analysis?.experience_level">
                  经验：{{ analysis.resume_analysis.experience_level }}
                </div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="analysis-card">
                <div class="analysis-label">JD 要求</div>
                <div class="analysis-value">{{ analysis.jd_analysis?.summary || '—' }}</div>
                <div class="analysis-detail" v-if="analysis.jd_analysis?.level">
                  级别：{{ analysis.jd_analysis.level }}
                </div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="analysis-card">
                <div class="analysis-label">匹配度</div>
                <div class="analysis-score">{{ analysis.match_gap?.overall_fit || '—' }}%</div>
                <el-tag
                  v-if="analysis.match_gap?.gap_areas?.length"
                  v-for="g in analysis.match_gap.gap_areas"
                  :key="g"
                  size="small"
                  type="warning"
                  class="gap-tag"
                >{{ g }}</el-tag>
              </div>
            </el-col>
          </el-row>
        </div>
      </div>
    </div>

    <!-- ═══ 阶段二：面试 ═══ -->
    <div v-if="phase === 'interview'" class="interview-container">
      <div class="interview-header">
        <div class="interview-progress">
          <span class="round-badge">第 {{ interviewState.round }} 轮</span>
          <el-progress
            :percentage="Math.round((interviewState.round / form.max_rounds) * 100)"
            :stroke-width="6"
            :show-text="false"
            class="progress-bar"
          />
        </div>
        <el-button text @click="endInterview">结束面试</el-button>
      </div>

      <div class="interview-main">
        <!-- 面试官区域 -->
        <div class="interviewer-section">
          <div class="interviewer-avatar">
            <el-avatar :size="44" icon="UserFilled" />
            <span class="interviewer-name">{{ personaName }}</span>
          </div>
          <div class="interviewer-bubble" v-if="interviewState.question">
            <p>{{ interviewState.question }}</p>
          </div>
        </div>

        <!-- 用户回答区域 -->
        <div class="answer-section" v-if="!interviewState.answered">
          <el-input
            v-model="currentAnswer"
            type="textarea"
            :rows="5"
            placeholder="输入你的回答..."
            :disabled="interviewState.submitting"
          />
          <div class="answer-actions">
            <span class="char-count">{{ currentAnswer.length }} 字</span>
            <el-button
              type="primary"
              :loading="interviewState.submitting"
              :disabled="!currentAnswer.trim()"
              @click="submitAnswer"
            >
              提交回答
            </el-button>
          </div>
        </div>

        <!-- 评分结果 -->
        <div v-if="interviewState.answered && lastScores" class="score-result">
          <el-divider>本轮评分</el-divider>
          <div class="score-grid">
            <div class="score-item">
              <div class="score-value" :class="scoreClass(lastScores.total)">{{ formatScore(lastScores.total) }}</div>
              <div class="score-label">总分</div>
              <el-tag :type="scoreTagType(lastScores.total)" size="small">{{ lastScores.answer_quality_label }}</el-tag>
            </div>
            <div class="score-item">
              <div class="score-sub">准确性</div>
              <el-progress :percentage="Math.round(lastScores.accuracy * 100)" :stroke-width="6" :color="progressColor(lastScores.accuracy)" />
            </div>
            <div class="score-item">
              <div class="score-sub">深度</div>
              <el-progress :percentage="Math.round(lastScores.depth * 100)" :stroke-width="6" :color="progressColor(lastScores.depth)" />
            </div>
            <div class="score-item">
              <div class="score-sub">覆盖度</div>
              <el-progress :percentage="Math.round(lastScores.completeness * 100)" :stroke-width="6" :color="progressColor(lastScores.completeness)" />
            </div>
            <div class="score-item">
              <div class="score-sub">清晰度</div>
              <el-progress :percentage="Math.round(lastScores.clarity * 100)" :stroke-width="6" :color="progressColor(lastScores.clarity)" />
            </div>
            <div class="score-item">
              <div class="score-sub">实战</div>
              <el-progress :percentage="Math.round(lastScores.practical * 100)" :stroke-width="6" :color="progressColor(lastScores.practical)" />
            </div>
          </div>
          <div class="route-badge" v-if="lastRoute">
            <el-tag :type="routeTagType(lastRoute)" effect="dark">下一轮 → {{ routeLabel(lastRoute) }}</el-tag>
          </div>
          <el-button type="primary" class="next-btn" @click="nextRound" v-if="!interviewState.final">
            进入下一轮
          </el-button>
        </div>
      </div>
    </div>

    <!-- ═══ 阶段三：总结 ═══ -->
    <div v-if="phase === 'summary'" class="summary-container">
      <div class="summary-card">
        <h2>面试总结</h2>
        <div class="summary-total">
          <div class="big-score">{{ formatScore(finalSummary.overall_score) }}</div>
          <div class="big-label">综合得分</div>
        </div>
        <div class="summary-grid">
          <div class="summary-item">
            <div class="summary-dim">准确性</div>
            <el-progress :percentage="Math.round(finalSummary.accuracy_avg * 100)" :stroke-width="8" color="#409EFF" />
          </div>
          <div class="summary-item">
            <div class="summary-dim">深度</div>
            <el-progress :percentage="Math.round(finalSummary.depth_avg * 100)" :stroke-width="8" color="#67C23A" />
          </div>
          <div class="summary-item">
            <div class="summary-dim">覆盖度</div>
            <el-progress :percentage="Math.round(finalSummary.completeness_avg * 100)" :stroke-width="8" color="#E6A23C" />
          </div>
          <div class="summary-item">
            <div class="summary-dim">清晰度</div>
            <el-progress :percentage="Math.round(finalSummary.clarity_avg * 100)" :stroke-width="8" color="#F56C6C" />
          </div>
          <div class="summary-item">
            <div class="summary-dim">实战</div>
            <el-progress :percentage="Math.round(finalSummary.practical_avg * 100)" :stroke-width="8" color="#909399" />
          </div>
        </div>
        <div class="summary-detail" v-if="finalSummary.strengths?.length || finalSummary.weaknesses?.length">
          <el-row :gutter="16">
            <el-col :span="12" v-if="finalSummary.strengths?.length">
              <h3>优势</h3>
              <el-tag v-for="s in finalSummary.strengths" :key="s" type="success" effect="plain" class="strength-tag">{{ s }}</el-tag>
            </el-col>
            <el-col :span="12" v-if="finalSummary.weaknesses?.length">
              <h3>待提升</h3>
              <el-tag v-for="w in finalSummary.weaknesses" :key="w" type="warning" effect="plain" class="strength-tag">{{ w }}</el-tag>
            </el-col>
          </el-row>
        </div>
        <el-button type="primary" size="large" @click="resetInterview" class="restart-btn">再来一次</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const PERSONA_MAP = {
  ali_p7: { name: '阿里 P7 压力面', style: '追问式', depth: '4/5' },
  tencent_t9: { name: '腾讯 T9 技术面', style: '引导式', depth: '5/5' },
  bytedance_22: { name: '字节 2-2 系统设计', style: '追问式', depth: '4/5' },
  foreign_friendly: { name: '外企友好面', style: '引导式', depth: '3/5' },
  huawei_expert: { name: '华为技术专家', style: '压力式', depth: '4/5' },
  startup_cto: { name: '初创公司 CTO', style: '开放式', depth: '3/5' },
  meituan_l8: { name: '美团 L8 业务面', style: '追问式', depth: '4/5' },
  campus_basic: { name: '校招基础面', style: '引导式', depth: '2/5' },
  promotion_defense: { name: '晋升答辩', style: '追问式', depth: '5/5' },
  free_mode: { name: '自由模式', style: '开放式', depth: '3/5' },
}

const personas = Object.entries(PERSONA_MAP).map(([id, info]) => ({ id, ...info }))

const phase = ref('setup')
const starting = ref(false)
const currentAnswer = ref('')
const roomId = ref('')
const analysis = ref(null)

const form = ref({
  resume: '',
  jd: '',
  persona_id: 'free_mode',
  max_rounds: 10,
})

const interviewState = ref({
  round: 0,
  question: '',
  submitting: false,
  answered: false,
  final: false,
})

const lastScores = ref(null)
const lastRoute = ref('')
const finalSummary = ref({})

const personaName = computed(() => PERSONA_MAP[form.value.persona_id]?.name || '')
const personaDepth = computed(() => PERSONA_MAP[form.value.persona_id]?.depth || '')

const token = () => localStorage.getItem('token') || ''

const formatScore = (v) => {
  if (v == null) return '—'
  return (v * 100).toFixed(0)
}

const scoreClass = (v) => {
  if (v >= 0.80) return 'score-excellent'
  if (v >= 0.50) return 'score-good'
  return 'score-low'
}

const scoreTagType = (v) => {
  if (v >= 0.80) return 'success'
  if (v >= 0.50) return 'warning'
  return 'danger'
}

const progressColor = (v) => {
  if (v >= 0.80) return '#67C23A'
  if (v >= 0.50) return '#E6A23C'
  return '#F56C6C'
}

const routeTagType = (r) => {
  if (r === 'derivative') return 'success'
  if (r === 'extension') return 'warning'
  if (r === 'prerequisite') return 'danger'
  return 'info'
}

const routeLabel = (r) => {
  if (r === 'derivative') return '深入挖掘'
  if (r === 'extension') return '横向拓展'
  if (r === 'prerequisite') return '回退基础'
  return r
}

const startInterview = async () => {
  starting.value = true
  try {
    const resp = await fetch('/api/interview/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token()}` },
      body: JSON.stringify(form.value),
    })
    if (!resp.ok) {
      const err = await resp.json()
      throw new Error(err.detail || '启动失败')
    }
    const data = await resp.json()
    roomId.value = data.room_id
    analysis.value = data
    interviewState.value.round = 1
    interviewState.value.question = data.first_question
    interviewState.value.answered = false
    interviewState.value.final = false
    phase.value = 'interview'
  } catch (e) {
    ElMessage.error('面试启动失败：' + (e.message || '未知错误'))
  } finally {
    starting.value = false
  }
}

const submitAnswer = async () => {
  interviewState.value.submitting = true
  try {
    const resp = await fetch('/api/interview/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token()}` },
      body: JSON.stringify({ room_id: roomId.value, answer: currentAnswer.value }),
    })
    if (!resp.ok) {
      const err = await resp.json()
      throw new Error(err.detail || '提交失败')
    }
    const data = await resp.json()
    interviewState.value.answered = true
    lastScores.value = data.scores
    lastRoute.value = data.route
    currentAnswer.value = ''
    // 保存下一题供 nextRound 使用
    if (data.next_question) {
      interviewState.value._nextQuestion = data.next_question
    }
    if (data.final) {
      interviewState.value.final = true
      await loadSummary()
    }
  } catch (e) {
    ElMessage.error('提交失败：' + (e.message || '未知错误'))
  } finally {
    interviewState.value.submitting = false
  }
}

const nextRound = async () => {
  // 使用 API 返回的下一题
  if (interviewState.value._nextQuestion) {
    interviewState.value.question = interviewState.value._nextQuestion
    interviewState.value._nextQuestion = ''
  }
  interviewState.value.round++
  interviewState.value.answered = false
  lastScores.value = null
  lastRoute.value = ''
}

const loadSummary = async () => {
  try {
    const resp = await fetch(`/api/interview/${roomId.value}/summary`, {
      headers: { Authorization: `Bearer ${token()}` },
    })
    if (resp.ok) {
      const data = await resp.json()
      finalSummary.value = data.summary
    }
  } catch { /* ignore */ }
}

const endInterview = async () => {
  await loadSummary()
  phase.value = 'summary'
}

const resetInterview = () => {
  phase.value = 'setup'
  roomId.value = ''
  analysis.value = null
  interviewState.value = { round: 0, question: '', submitting: false, answered: false, final: false }
  lastScores.value = null
  lastRoute.value = ''
  finalSummary.value = {}
}
</script>

<style scoped>
.interview-page { min-height: 100vh; background: #f5f7fa; padding: 24px; }

/* ═══ Setup ═══ */
.setup-container { max-width: 960px; margin: 0 auto; }
.setup-card {
  background: #fff; border-radius: 12px; padding: 32px;
  box-shadow: 0 2px 12px rgba(0,0,0,.06);
}
.setup-header { text-align: center; margin-bottom: 28px; }
.setup-header h2 { font-size: 24px; color: #303133; margin: 0 0 8px; }
.setup-header p { color: #909399; font-size: 14px; }
.full-width { width: 100%; }
.option-tag { float: right; color: #909399; font-size: 12px; }
.depth-tag { margin-top: 28px; font-size: 14px; padding: 6px 12px; }
.start-btn { width: 100%; margin-top: 20px; height: 44px; font-size: 16px; }
.analysis-section { margin-top: 24px; }
.analysis-card {
  background: #fafafa; border-radius: 8px; padding: 16px; text-align: center;
}
.analysis-label { font-size: 12px; color: #909399; margin-bottom: 8px; }
.analysis-value { font-size: 14px; color: #303133; line-height: 1.5; }
.analysis-detail { font-size: 12px; color: #606266; margin-top: 4px; }
.analysis-score { font-size: 28px; font-weight: 700; color: #409EFF; margin-bottom: 8px; }
.gap-tag { margin: 2px; }

/* ═══ Interview ═══ */
.interview-container { max-width: 800px; margin: 0 auto; }
.interview-header {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border-radius: 12px; padding: 16px 24px;
  box-shadow: 0 1px 8px rgba(0,0,0,.04); margin-bottom: 16px;
}
.interview-progress { flex: 1; margin-right: 16px; }
.round-badge { font-size: 14px; font-weight: 600; color: #409EFF; }
.progress-bar { margin-top: 6px; }
.interview-main { background: #fff; border-radius: 12px; padding: 32px; box-shadow: 0 2px 12px rgba(0,0,0,.06); }

.interviewer-section { display: flex; align-items: flex-start; gap: 16px; margin-bottom: 32px; }
.interviewer-avatar { display: flex; flex-direction: column; align-items: center; gap: 4px; flex-shrink: 0; }
.interviewer-name { font-size: 11px; color: #909399; white-space: nowrap; }
.interviewer-bubble {
  background: #f0f2f5; border-radius: 0 12px 12px 12px;
  padding: 16px 20px; font-size: 15px; line-height: 1.6; color: #303133;
  max-width: 600px;
}

.answer-section { margin-bottom: 24px; }
.answer-actions { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; }
.char-count { font-size: 12px; color: #909399; }

.score-result { margin-top: 8px; }
.score-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 16px 0; }
.score-item { text-align: center; }
.score-value { font-size: 36px; font-weight: 700; margin-bottom: 4px; }
.score-excellent { color: #67C23A; }
.score-good { color: #E6A23C; }
.score-low { color: #F56C6C; }
.score-label { font-size: 12px; color: #909399; margin-bottom: 6px; }
.score-sub { font-size: 12px; color: #606266; margin-bottom: 6px; text-align: left; }
.route-badge { text-align: center; margin: 16px 0; }
.route-badge .el-tag { font-size: 14px; padding: 6px 16px; }
.next-btn { width: 100%; margin-top: 16px; height: 40px; }

/* ═══ Summary ═══ */
.summary-container { max-width: 600px; margin: 0 auto; }
.summary-card {
  background: #fff; border-radius: 12px; padding: 40px; text-align: center;
  box-shadow: 0 2px 12px rgba(0,0,0,.06);
}
.summary-card h2 { font-size: 22px; color: #303133; margin: 0 0 24px; }
.summary-total { margin-bottom: 24px; }
.big-score { font-size: 56px; font-weight: 800; color: #409EFF; }
.big-label { font-size: 14px; color: #909399; margin-top: 4px; }
.summary-grid { display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px; }
.summary-item { text-align: left; }
.summary-dim { font-size: 13px; color: #606266; margin-bottom: 4px; }
.summary-detail { text-align: left; margin-bottom: 24px; }
.summary-detail h3 { font-size: 14px; color: #303133; margin: 8px 0; }
.strength-tag { margin: 3px; }
.restart-btn { width: 100%; height: 44px; }
</style>
