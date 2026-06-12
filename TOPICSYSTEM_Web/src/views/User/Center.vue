<template>
  <div class="user-center">
    <h1 class="page-title">用户中心</h1>

    <!-- 账户信息 -->
    <div class="card">
      <h2 class="card-title">账户信息</h2>
      <div class="info-row"><span class="label">用户名</span><span class="value">{{ user.username }}</span></div>
      <div class="info-row"><span class="label">邮箱</span><span class="value">{{ user.email }}</span></div>
      <div class="info-row"><span class="label">会员等级</span><span class="value">{{ user.is_admin ? '管理员' : '免费用户' }}</span></div>
      <div class="info-row"><span class="label">题目配额</span><span class="value">{{ user.topic_credits }} 次</span></div>
      <div class="info-row"><span class="label">对话配额</span><span class="value">{{ user.agent_credits }} 次</span></div>
    </div>

    <!-- 学习偏好 -->
    <div class="card">
      <h2 class="card-title">学习偏好</h2>
      <el-form :model="prefs" label-position="top">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="目标岗位">
              <el-select v-model="prefs.target_position" placeholder="请选择" clearable style="width:100%">
                <el-option v-for="p in positions" :key="p.id" :label="p.name" :value="p.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="经验水平">
              <el-radio-group v-model="prefs.experience_level">
                <el-radio value="初级">初级</el-radio>
                <el-radio value="中级">中级</el-radio>
                <el-radio value="高级">高级</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="学习偏好">
          <el-select v-model="prefs.learning_preference" multiple placeholder="选择偏好方向" style="width:100%">
            <el-option v-for="t in tagOptions" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="每日目标 (题)">
          <el-input-number v-model="prefs.today_target" :min="0" :max="50" />
        </el-form-item>
        <el-button type="primary" :loading="saving" @click="savePrefs">保存偏好</el-button>
      </el-form>
    </div>

    <!-- 修改密码 -->
    <div class="card">
      <h2 class="card-title">修改密码</h2>
      <el-form :model="pwdForm" label-position="top">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="旧密码">
              <el-input v-model="pwdForm.old_password" type="password" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="新密码">
              <el-input v-model="pwdForm.new_password" type="password" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="&nbsp;">
              <el-button type="warning" :loading="pwdSaving" @click="changePwd">修改密码</el-button>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

const tagOptions = ['Java', 'Python', '前端', '数据库', 'Spring', 'Redis', '分布式', '消息队列', '算法', '系统设计']
const saving = ref(false)
const pwdSaving = ref(false)
const positions = ref([])

const user = reactive({ username: '', email: '', is_admin: false, topic_credits: 0, agent_credits: 0 })
const prefs = reactive({ target_position: '', learning_preference: [], experience_level: '', today_target: 0 })
const pwdForm = reactive({ old_password: '', new_password: '' })

onMounted(async () => {
  try {
    const me = await request.get('/auth/me')
    Object.assign(user, me)
    prefs.target_position = me.target_position || ''
    prefs.learning_preference = (me.learning_preference || '').split(',').filter(Boolean)
    prefs.experience_level = me.experience_level || ''
    prefs.today_target = me.today_target || 0
    const pos = await request.get('/topic/positions')
    positions.value = pos.items || []
  } catch {}
})

async function savePrefs() {
  saving.value = true
  try {
    await request.post('/auth/preferences', {
      target_position: prefs.target_position,
      learning_preference: (prefs.learning_preference || []).join(','),
      experience_level: prefs.experience_level,
      today_target: prefs.today_target
    })
    ElMessage.success('偏好已保存')
  } catch { ElMessage.error('保存失败') }
  saving.value = false
}

async function changePwd() {
  pwdSaving.value = true
  try {
    await request.post('/auth/change-password', pwdForm)
    ElMessage.success('密码已修改')
    pwdForm.old_password = ''; pwdForm.new_password = ''
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  }
  pwdSaving.value = false
}
</script>

<style scoped>
.user-center { max-width: 800px; margin: 0 auto; padding: 32px 20px; }
.page-title { font-size: 28px; font-weight: 700; margin: 0 0 24px; }
.card { background: #fff; border-radius: 14px; padding: 28px; margin-bottom: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.04); }
.card-title { font-size: 18px; font-weight: 700; margin: 0 0 20px; padding-bottom: 12px; border-bottom: 1px solid #f1f2f3; }
.info-row { display: flex; justify-content: space-between; padding: 8px 0; font-size: 14px; }
.info-row .label { color: #999; }
.info-row .value { color: #333; font-weight: 500; }
</style>
