<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="brand">TopicSystem</h1>
      <p class="subtitle">登录以继问题库</p>
      <el-form :model="form" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="your@email.com" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="••••••" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-button type="primary" :loading="loading" class="login-btn" @click="handleLogin">登 录</el-button>
        <el-button text class="register-link" @click="showRegister = !showRegister">
          {{ showRegister ? '已有账号？去登录' : '没有账号？去注册' }}
        </el-button>
      </el-form>

      <!-- 注册 -->
      <el-form v-if="showRegister" :model="regForm" label-position="top" @submit.prevent="handleRegister">
        <el-form-item label="用户名">
          <el-input v-model="regForm.username" placeholder="用户名" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="regForm.email" placeholder="your@email.com" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="regForm.password" type="password" placeholder="至少6位" show-password />
        </el-form-item>
        <el-button type="success" :loading="regLoading" class="login-btn" @click="handleRegister">注 册</el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const loading = ref(false)
const regLoading = ref(false)
const showRegister = ref(false)

const form = reactive({ email: '', password: '' })
const regForm = reactive({ username: '', email: '', password: '' })

const api = axios.create({ baseURL: '/api', timeout: 10000 })

async function handleLogin() {
  loading.value = true
  try {
    const res = await api.post('/auth/login', { email: form.email, password: form.password })
    localStorage.setItem('token', res.data.access_token)
    localStorage.setItem('user', JSON.stringify({ email: form.email }))
    router.push('/dashboard')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally { loading.value = false }
}

async function handleRegister() {
  regLoading.value = true
  try {
    const res = await api.post('/auth/register', {
      username: regForm.username, email: regForm.email, password: regForm.password
    })
    localStorage.setItem('token', res.data.access_token)
    localStorage.setItem('user', JSON.stringify({ email: regForm.email, username: regForm.username }))
    router.push('/dashboard')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '注册失败')
  } finally { regLoading.value = false }
}
</script>

<style scoped>
.login-page { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f0f2f5; }
.login-card { background: #fff; border-radius: 14px; padding: 48px 40px; width: 400px; box-shadow: 0 8px 40px rgba(0,0,0,0.06); }
.brand { font-size: 26px; font-weight: 800; color: #6366f1; text-align: center; margin: 0 0 4px; }
.subtitle { text-align: center; color: #999; font-size: 14px; margin: 0 0 28px; }
.login-btn { width: 100%; height: 44px; font-size: 15px; border-radius: 10px; margin-top: 8px; }
.register-link { width: 100%; margin-top: 12px; }
</style>
