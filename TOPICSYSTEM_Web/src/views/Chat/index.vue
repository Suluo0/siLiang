<template>
  <div class="chat-page">
    <!-- 主内容区 -->
    <main class="chat-main">
      <!-- 居中的对话区域 -->
      <div class="chat-container">
        <!-- 欢迎界面 -->
        <div v-if="messages.length === 0" class="welcome-section">
          <div class="welcome-header">
            <div class="brand-logo">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="url(#logoGrad)" stroke-width="2"/>
                <path d="M8 12h8M12 8v8" stroke="url(#logoGrad)" stroke-width="2" stroke-linecap="round"/>
                <defs>
                  <linearGradient id="logoGrad" x1="0" y1="0" x2="24" y2="24">
                    <stop offset="0%" stop-color="#667eea"/>
                    <stop offset="100%" stop-color="#764ba2"/>
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <h1 class="welcome-title">
              <span class="gradient-text">拓扑客</span>
            </h1>
            <p class="welcome-desc">告诉我你想学习什么，我来为你构建知识图谱</p>
          </div>

          <!-- 联想词区域 -->
          <div class="suggestions-section">
            <p class="suggestions-label">试试这些话题</p>
            <div class="suggestion-cards">
              <button class="suggestion-card" @click="sendExample('HashMap 底层实现原理')">
                <span class="card-icon">🌲</span>
                <span class="card-text">HashMap 底层实现原理</span>
              </button>
              <button class="suggestion-card" @click="sendExample('Python 装饰器工作原理')">
                <span class="card-icon">⚡</span>
                <span class="card-text">Python 装饰器工作原理</span>
              </button>
              <button class="suggestion-card" @click="sendExample('React Hooks 使用指南')">
                <span class="card-icon">⚛️</span>
                <span class="card-text">React Hooks 使用指南</span>
              </button>
              <button class="suggestion-card" @click="sendExample('微服务架构设计模式')">
                <span class="card-icon">🏗️</span>
                <span class="card-text">微服务架构设计模式</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <div v-else class="messages-section">
          <div class="messages-wrapper">
            <div 
              v-for="(msg, index) in messages" 
              :key="index" 
              class="message-item"
              :class="msg.type"
            >
              <div class="message-avatar">
                <span v-if="msg.type === 'user'">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                  </svg>
                </span>
                <span v-else>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="#667eea" stroke-width="2"/>
                    <path d="M8 12h8M12 8v8" stroke="#667eea" stroke-width="2" stroke-linecap="round"/>
                  </svg>
                </span>
              </div>
              <div class="message-content">
                <p class="message-text">{{ msg.text }}</p>
                
                <!-- 主题卡片 -->
                <div v-if="msg.topic" class="topic-card">
                  <div class="topic-header">
                    <h4>{{ msg.topic.topic_name }}</h4>
                    <span class="topic-badge">{{ msg.topic.domain }}</span>
                  </div>
                  
                  <div class="topic-meta">
                    <div class="meta-item">
                      <span class="meta-label">难度</span>
                      <div class="difficulty">
                        <span v-for="n in 5" :key="n" class="star" :class="{ active: n <= (msg.topic.difficulty || 3) }">★</span>
                      </div>
                    </div>
                    <div class="meta-item" v-if="msg.topic.tags?.length">
                      <span class="meta-label">标签</span>
                      <div class="tags">
                        <span v-for="tag in msg.topic.tags" :key="tag" class="tag">{{ tag }}</span>
                      </div>
                    </div>
                  </div>
                  
                  <button class="btn-learn" @click="viewTopic(msg.topic.topic_id)">
                    开始学习
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M5 12h14M12 5l7 7-7 7"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            <!-- 加载状态 -->
            <div v-if="isLoading" class="message-item assistant">
              <div class="message-avatar">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="#667eea" stroke-width="2"/>
                  <path d="M8 12h8M12 8v8" stroke="#667eea" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </div>
              <div class="message-content">
                <div class="loading-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="input-section">
          <div class="input-wrapper">
            <input
              v-model="userInput"
              @keydown.enter.exact.prevent="sendMessage"
              type="text"
              placeholder="输入你想学习的主题..."
              :disabled="isLoading"
              class="chat-input"
            />
            <button 
              @click="sendMessage" 
              :disabled="!userInput.trim() || isLoading"
              class="send-btn"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
              </svg>
            </button>
          </div>
          <p class="input-hint">按 Enter 发送</p>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const userInput = ref('')
const messages = ref([])
const isLoading = ref(false)
const messagesContainer = ref(null)

// 发送示例
const sendExample = (text) => {
  userInput.value = text
  sendMessage()
}

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim() || isLoading.value) return

  const text = userInput.value.trim()
  userInput.value = ''

  // 添加用户消息
  messages.value.push({
    type: 'user',
    text: text
  })

  await nextTick()
  scrollToBottom()

  isLoading.value = true

  try {
    // 使用 v3 Agent API
    const token = localStorage.getItem('token') || ''
    const response = await fetch('/api/v3/topic/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ user_input: text })
    })

    const data = await response.json()
    
    const assistantMsg = {
      type: 'assistant',
      topic: data.topic_name || '',
      domain: data.domain || '',
      source: data.source || '',
      trace: data.trace_id || ''
    }
    messages.value.push(assistantMsg)
    
  } catch (error) {
    messages.value.push({
      type: 'error',
      text: 'Agent 调用失败: ' + (error.message || '未知错误')
    })
  } finally {
    isLoading.value = false
    await nextTick()
    scrollToBottom()
  }
}

// 查看主题详情
const viewTopic = (topicId) => {
  console.log('查看主题:', topicId)
  router.push(`/topic/detail/${topicId}`)
}

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}
</script>

<style scoped>
/* 整体布局 */
.chat-page {
  min-height: calc(100vh - 72px);
  background: #f5f7fa;
  display: flex;
  flex-direction: column;
}

.chat-main {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 0 32px 32px;
}

.chat-container {
  width: 100%;
  max-width: 720px;
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 72px - 64px);
}

/* 欢迎区域 */
.welcome-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 60px 0;
  text-align: center;
}

.welcome-header {
  margin-bottom: 48px;
}

.brand-logo {
  margin-bottom: 24px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.welcome-title {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 16px;
  color: #303133;
}

.gradient-text {
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.welcome-desc {
  font-size: 16px;
  color: #909399;
  line-height: 1.6;
}

/* 联想词区域 */
.suggestions-section {
  width: 100%;
}

.suggestions-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.suggestion-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.suggestion-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 24px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: left;
}

.suggestion-card:hover {
  border-color: #667eea;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.15);
  transform: translateY(-2px);
}

.card-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.card-text {
  font-size: 15px;
  color: #303133;
  font-weight: 500;
  line-height: 1.4;
}

/* 消息区域 */
.messages-section {
  flex: 1;
  overflow-y: auto;
  padding: 24px 0;
}

.messages-wrapper {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.message-item {
  display: flex;
  gap: 16px;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 50%;
  flex-shrink: 0;
  color: #667eea;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.message-item.user .message-avatar {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
}

.message-content {
  flex: 1;
  max-width: calc(100% - 60px);
}

.message-text {
  margin: 0;
  padding: 14px 18px;
  background: #fff;
  border-radius: 12px;
  border-top-left-radius: 4px;
  font-size: 15px;
  line-height: 1.6;
  color: #303133;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.message-item.user .message-text {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  border-radius: 12px;
  border-top-right-radius: 4px;
}

/* 主题卡片 */
.topic-card {
  margin-top: 16px;
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #ebeef5;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.topic-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.topic-header h4 {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.topic-badge {
  padding: 4px 12px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  color: #fff;
}

.topic-meta {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.meta-label {
  font-size: 13px;
  color: #909399;
  min-width: 36px;
}

.difficulty {
  display: flex;
  gap: 2px;
}

.star {
  color: #dcdfe6;
  font-size: 14px;
}

.star.active {
  color: #f7ba2a;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  padding: 4px 10px;
  background: #f4f4f5;
  border-radius: 6px;
  font-size: 12px;
  color: #606266;
}

.btn-learn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-learn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.35);
}

/* 加载动画 */
.loading-dots {
  display: flex;
  gap: 4px;
  padding: 14px 18px;
  background: #fff;
  border-radius: 12px;
  border-top-left-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.loading-dots span {
  width: 8px;
  height: 8px;
  background: #667eea;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}

.loading-dots span:nth-child(1) { animation-delay: -0.32s; }
.loading-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* 输入区域 */
.input-section {
  padding: 20px 0 0;
  border-top: 1px solid #ebeef5;
  background: #f5f7fa;
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 24px;
  transition: all 0.3s ease;
}

.input-wrapper:focus-within {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.chat-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-size: 15px;
  color: #303133;
  font-family: inherit;
}

.chat-input::placeholder {
  color: #c0c4cc;
}

.chat-input:disabled {
  opacity: 0.6;
}

.send-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border: none;
  border-radius: 50%;
  color: #fff;
  cursor: pointer;
  transition: all 0.3s ease;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.35);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input-hint {
  margin-top: 10px;
  font-size: 12px;
  color: #c0c4cc;
  text-align: center;
}

/* 滚动条 */
.messages-section::-webkit-scrollbar {
  width: 6px;
}

.messages-section::-webkit-scrollbar-track {
  background: transparent;
}

.messages-section::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 3px;
}

.messages-section::-webkit-scrollbar-thumb:hover {
  background: #c0c4cc;
}

/* 响应式 */
@media (max-width: 768px) {
  .chat-main {
    padding: 0 16px 16px;
  }
  
  .welcome-title {
    font-size: 28px;
  }
  
  .suggestion-cards {
    grid-template-columns: 1fr;
  }
  
  .suggestion-card {
    padding: 16px 20px;
  }
}
</style>
