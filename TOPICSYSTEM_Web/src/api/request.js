import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截：自动注入 JWT
request.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：401 时尝试刷新 token
let isRefreshing = false
let refreshQueue = []

request.interceptors.response.use(
  response => response.data,
  async error => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken && !isRefreshing) {
        originalRequest._retry = true
        isRefreshing = true
        try {
          const res = await axios.post('/api/auth/refresh', { refresh_token: refreshToken })
          const newToken = res.data.access_token
          localStorage.setItem('token', newToken)
          localStorage.setItem('refresh_token', res.data.refresh_token)
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          refreshQueue.forEach(cb => cb(newToken))
          refreshQueue = []
          isRefreshing = false
          return request(originalRequest)
        } catch {
          isRefreshing = false
          localStorage.removeItem('token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user')
          window.location.href = '/login'
          return Promise.reject(error)
        }
      }
    }
    if (error.response?.status !== 401) {
      ElMessage.error(error.response?.data?.detail || error.message || '请求失败')
    }
    return Promise.reject(error)
  }
)

export default request
