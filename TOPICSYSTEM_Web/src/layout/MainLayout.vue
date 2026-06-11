<template>
  <div class="main-layout">
    <!-- 顶边栏 -->
    <header class="header">
      <div class="header-left">
        <h1 class="logo" @click="goHome">拓扑客</h1>
        <nav class="nav-menu">
          <a href="#" class="nav-item" @click.prevent="goToHome">主页</a>
          <a href="#" class="nav-item" @click.prevent="goToLibrary">题库</a>
          <a href="#" class="nav-item">面经</a>
          <a href="#" class="nav-item">模拟面试</a>
          <a href="#" class="nav-item">交流社区</a>
        </nav>
      </div>
      <div class="header-right">
        <!-- 搜索区域 -->
        <div class="search-wrapper" :class="{ expanded: isSearchExpanded }">
          <transition name="search-expand">
            <el-input
              v-if="isSearchExpanded"
              v-model="searchQuery"
              placeholder="搜索主题、内容..."
              class="search-input"
              @blur="handleSearchBlur"
              @keyup.enter="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </transition>
          <el-button
            class="search-btn"
            :class="{ active: isSearchExpanded }"
            @click="toggleSearch"
          >
            <el-icon v-if="!isSearchExpanded"><Search /></el-icon>
            <el-icon v-else><Close /></el-icon>
          </el-button>
        </div>

        <el-dropdown>
          <span class="user-info">
            <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
            <span class="username">管理员</span>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="handleLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Close } from '@element-plus/icons-vue'

const router = useRouter()

const isSearchExpanded = ref(false)
const searchQuery = ref('')

const toggleSearch = () => {
  isSearchExpanded.value = !isSearchExpanded.value
  if (!isSearchExpanded.value) {
    searchQuery.value = ''
  }
}

const handleSearchBlur = () => {
  if (!searchQuery.value) {
    isSearchExpanded.value = false
  }
}

const handleSearch = () => {
  if (searchQuery.value) {
    router.push('/topic/library')
  }
}

const goToLibrary = () => {
  router.push('/topic/library')
}

const goHome = () => {
  router.push('/dashboard')
}

const goToHome = () => {
  router.push('/dashboard')
}

const handleLogout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}
</script>

<style scoped>
/* ── 全局滚动修复 ── */
.main-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f7fa;
  overflow: hidden;
}

.header {
  flex-shrink: 0;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  height: 72px;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  z-index: 100;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.logo {
  font-size: 20px;
  font-weight: 700;
  color: #667eea;
  margin: 0;
  cursor: pointer;
}

.nav-menu {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-item {
  padding: 8px 16px;
  font-size: 15px;
  color: #606266;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.nav-item:hover {
  color: #667eea;
  background: rgba(102, 126, 234, 0.08);
}

.nav-item.active {
  color: #667eea;
  background: rgba(102, 126, 234, 0.1);
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-input {
  width: 0;
  opacity: 0;
  transition: all 0.3s ease;
}

.search-wrapper.expanded .search-input {
  width: 240px;
  opacity: 1;
}

.search-btn {
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 10px;
  border: none;
  background: #f5f7fa;
  color: #606266;
  transition: all 0.3s ease;
}

.search-btn:hover {
  background: #667eea;
  color: #fff;
}

.search-btn.active {
  background: #667eea;
  color: #fff;
}

.search-expand-enter-active,
.search-expand-leave-active {
  transition: all 0.3s ease;
}

.search-expand-enter-from,
.search-expand-leave-to {
  width: 0;
  opacity: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.username {
  color: #606266;
}

@media (max-width: 1024px) {
  .nav-menu { display: none; }
}

@media (max-width: 768px) {
  .header { padding: 0 16px; }
  .username { display: none; }
  .main-content { padding: 16px; }
}
</style>
