<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="brand">思量</h1>

      <!-- ═══ 登录 ═══ -->
      <template v-if="!showRegister">
        <p class="subtitle">登录账号</p>
        <el-form :model="loginForm" label-position="top">
          <el-form-item label="用户名">
            <el-input v-model="loginForm.username" placeholder="用户名" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="loginForm.password" type="password" placeholder="••••••" show-password @keyup.enter="handleLogin" />
          </el-form-item>
          <el-form-item label="验证码">
            <div class="captcha-row">
              <el-input v-model="loginForm.captcha" placeholder="4位数字" maxlength="4" class="captcha-input" />
              <span class="captcha-text" @click="refreshCaptcha">{{ captchaText || '----' }}</span>
            </div>
          </el-form-item>
          <el-button type="primary" :loading="loginLoading" class="submit-btn" @click="handleLogin">登 录</el-button>
          <el-button text class="toggle-link" @click="showRegister = true">没有账号？去注册</el-button>
        </el-form>
      </template>

      <!-- ═══ 注册 ═══ -->
      <template v-else>
        <p class="subtitle">注册账号</p>
        <el-form :model="regForm" label-position="top">
          <el-form-item label="用户名">
            <el-input v-model="regForm.username" placeholder="用户名（至少2位）" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="regForm.password" type="password" placeholder="至少6位" show-password />
          </el-form-item>
          <el-form-item label="验证码">
            <div class="captcha-row">
              <el-input v-model="regForm.captcha" placeholder="4位数字" maxlength="4" class="captcha-input" />
              <span class="captcha-text" @click="refreshCaptcha">{{ captchaText || '----' }}</span>
            </div>
          </el-form-item>
          <el-form-item label="邮箱">
            <div class="captcha-row">
              <el-input v-model="regForm.email" placeholder="your@email.com" class="captcha-input" />
              <el-button size="small" type="success" :disabled="!canSendCode" :loading="sendingCode" @click="sendCode" class="send-btn">发送验证码</el-button>
            </div>
          </el-form-item>
          <el-form-item label="邮箱验证码">
            <el-input v-model="regForm.emailCode" placeholder="6位验证码" maxlength="6" />
          </el-form-item>
          <el-button type="primary" :loading="regLoading" :disabled="!canRegister" class="submit-btn" @click="handleRegister">注 册</el-button>
          <el-button text class="toggle-link" @click="showRegister = false">已有账号？去登录</el-button>
        </el-form>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const api = axios.create({ baseURL: '/api', timeout: 15000 })

const showRegister = ref(false)
const loginLoading = ref(false)
const regLoading = ref(false)
const sendingCode = ref(false)
const captchaId = ref('')
const captchaText = ref('')

const loginForm = reactive({ username: '', password: '', captcha: '' })
const regForm = reactive({ username: '', password: '', captcha: '', email: '', emailCode: '' })

const emailValid = computed(() => /^[\w\.-]+@[\w\.-]+\.\w+$/.test(regForm.email))
const captchaValid = computed(() => regForm.captcha.length === 4)
const canSendCode = computed(() => emailValid.value && captchaValid.value)
const canRegister = computed(() =>
  regForm.username.length >= 2 && regForm.password.length >= 6 &&
  captchaValid.value && emailValid.value && regForm.emailCode.length === 6
)

async function refreshCaptcha() {
  try {
    const res = await api.get('/auth/captcha')
    captchaId.value = res.data.captcha_id
    captchaText.value = res.data.captcha_text
  } catch { ElMessage.error('获取验证码失败') }
}

async function handleLogin() {
  if (!loginForm.username || !loginForm.password || !loginForm.captcha) {
    return ElMessage.warning('请填写完整')
  }
  loginLoading.value = true
  try {
    const res = await api.post('/auth/login', {
      username: loginForm.username, password: loginForm.password,
      captcha_id: captchaId.value, captcha_answer: loginForm.captcha
    })
    _saveToken(res.data, loginForm.username, '')
    router.push('/dashboard')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
    refreshCaptcha()
  } finally { loginLoading.value = false }
}

async function sendCode() {
  if (!canSendCode.value) return
  sendingCode.value = true
  try {
    await api.post('/auth/send-code', {
      email: regForm.email, captcha_id: captchaId.value, captcha_answer: regForm.captcha
    })
    ElMessage.success('验证码已发送')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '发送失败')
    refreshCaptcha()
  } finally { sendingCode.value = false }
}

async function handleRegister() {
  if (!canRegister.value) return ElMessage.warning('请填写完整')
  regLoading.value = true
  try {
    const res = await api.post('/auth/register', {
      username: regForm.username, email: regForm.email, password: regForm.password,
      captcha_id: captchaId.value, captcha_answer: regForm.captcha, email_code: regForm.emailCode
    })
    _saveToken(res.data, regForm.username, regForm.email)
    router.push('/dashboard')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '注册失败')
    refreshCaptcha()
  } finally { regLoading.value = false }
}

function _saveToken(data, uname, uemail) {
  localStorage.setItem('token', data.access_token)
  localStorage.setItem('user', JSON.stringify({ username: uname || '', email: uemail || '' }))
}

onMounted(() => refreshCaptcha())
</script>

<style scoped>
.login-page { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f0f2f5; }
.login-card { background: #fff; border-radius: 14px; padding: 40px 36px; width: 420px; box-shadow: 0 8px 40px rgba(0,0,0,0.06); }
.brand { font-size: 26px; font-weight: 800; color: #6366f1; text-align: center; margin: 0; }
.subtitle { text-align: center; color: #999; font-size: 14px; margin: 8px 0 24px; }
.captcha-row { display: flex; align-items: center; gap: 12px; width: 100%; }
.captcha-input { flex: 1; }
.captcha-text {
  font-size: 26px; font-weight: 800; letter-spacing: 6px; color: #6366f1;
  background: #f0f3ff; padding: 4px 14px; border-radius: 8px; cursor: pointer;
  user-select: none; min-width: 100px; text-align: center;
}
.send-btn { flex-shrink: 0; white-space: nowrap; }
.submit-btn { width: 100%; height: 44px; font-size: 15px; border-radius: 10px; margin-top: 4px; }
.toggle-link { width: 100%; margin-top: 10px; }
</style>
