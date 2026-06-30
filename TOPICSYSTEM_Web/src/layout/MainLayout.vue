<template>
  <div class="main-layout">
    <!-- 顶边栏 -->
    <header class="header">
      <div class="header-left">
        <!-- 移动端汉堡菜单按钮(自绘三横线 SVG,el-icon Menu 是九宫格不合适) -->
        <button
          v-if="isMobile"
          class="menu-toggle"
          type="button"
          @click="drawerOpen = true"
          aria-label="打开菜单"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
            <line x1="4" y1="7"  x2="20" y2="7"  />
            <line x1="4" y1="12" x2="20" y2="12" />
            <line x1="4" y1="17" x2="20" y2="17" />
          </svg>
        </button>

        <h1 class="logo" @click="goHome">思量</h1>

        <!-- 桌面端导航(<md 隐藏) -->
        <nav class="nav-menu" v-if="!isMobile">
          <template v-for="item in navItems" :key="item.label">
            <!-- 带二级菜单:hover 展开下拉 -->
            <div v-if="item.children" class="nav-dropdown">
              <a
                href="#"
                class="nav-item"
                :class="{ active: isNavActive(item) }"
                @click.prevent
              >{{ item.label }}<el-icon class="nav-caret"><ArrowDown /></el-icon></a>
              <div class="nav-submenu">
                <a
                  v-for="sub in item.children"
                  :key="sub.path"
                  href="#"
                  class="nav-subitem"
                  :class="{ active: isPathActive(sub.path) }"
                  @click.prevent="handleNav(sub)"
                >{{ sub.label }}</a>
              </div>
            </div>
            <!-- 普通一级项 -->
            <a
              v-else
              href="#"
              class="nav-item"
              :class="{ active: isNavActive(item) }"
              @click.prevent="handleNav(item)"
            >{{ item.label }}</a>
          </template>
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
            <span class="username">{{ displayName }}</span>
          </span>
          <template #dropdown>
            <el-dropdown-menu v-if="isLoggedIn">
              <el-dropdown-item @click="goUserCenter">用户中心</el-dropdown-item>
              <el-dropdown-item @click="handleLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
            <el-dropdown-menu v-else>
              <el-dropdown-item @click="goLogin">登录</el-dropdown-item>
              <el-dropdown-item @click="goLogin">注册</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view />
    </main>

    <!-- 移动端抽屉菜单 -->
    <el-drawer
      v-model="drawerOpen"
      direction="ltr"
      size="78%"
      :with-header="false"
      :show-close="false"
      class="mobile-drawer"
    >
      <div class="drawer-content">
        <div class="drawer-header">
          <h2 class="drawer-logo" @click="navigateAndClose('/dashboard')">思量</h2>
          <el-button text @click="drawerOpen = false" aria-label="关闭菜单">
            <el-icon :size="22"><Close /></el-icon>
          </el-button>
        </div>

        <nav class="drawer-nav">
          <template v-for="item in navItems" :key="item.label">
            <!-- 带二级菜单:展示一级标题 + 缩进子项 -->
            <div v-if="item.children" class="drawer-group">
              <div class="drawer-group-label">{{ item.label }}</div>
              <a
                v-for="sub in item.children"
                :key="sub.path"
                href="#"
                class="drawer-nav-item drawer-subitem"
                :class="{ active: isPathActive(sub.path) }"
                @click.prevent="handleNav(sub, true)"
              >
                <span class="drawer-nav-label">{{ sub.label }}</span>
                <el-icon class="drawer-nav-arrow"><ArrowRight /></el-icon>
              </a>
            </div>
            <!-- 普通一级项 -->
            <a
              v-else
              href="#"
              class="drawer-nav-item"
              :class="{ active: isNavActive(item) }"
              @click.prevent="handleNav(item, true)"
            >
              <span class="drawer-nav-label">{{ item.label }}</span>
              <el-icon class="drawer-nav-arrow"><ArrowRight /></el-icon>
            </a>
          </template>
        </nav>

        <div class="drawer-footer">
          <template v-if="isLoggedIn">
            <el-button class="drawer-action" @click="navigateAndClose('/user-center')">用户中心</el-button>
            <el-button class="drawer-action" type="danger" plain @click="handleLogout">退出登录</el-button>
          </template>
          <template v-else>
            <el-button class="drawer-action" type="primary" @click="navigateAndClose('/login')">登录 / 注册</el-button>
          </template>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Search, Close, ArrowRight, ArrowDown } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useBreakpoints } from '@vueuse/core'

const router = useRouter()
const route = useRoute()

// ─── 响应式断点(对齐 tokens.css 4 档)───
const breakpoints = useBreakpoints({
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
})
const isMobile = breakpoints.smaller('md')   // < 768

// ─── 状态 ───
const isSearchExpanded = ref(false)
const searchQuery = ref('')
const drawerOpen = ref(false)

// 路由切换时自动关抽屉
watch(() => route.fullPath, () => { drawerOpen.value = false })

// ─── 导航项配置(单一数据源,桌面 + 抽屉共用)───
// children 表示二级菜单;有 children 的一级项本身不跳转,只展开
const navItems = [
  { label: '主页', path: '/dashboard' },
  {
    label: '题库',
    children: [
      { label: '背题', path: '/topic/library' },
      { label: '刷题', path: '/topic/practice' },
    ],
  },
  { label: '面经', coming: true },
  { label: '模拟面试', path: '/interview' },
  { label: '交流社区', coming: true },
]

// 一级项高亮:自身 path 命中,或任一子项命中
const isNavActive = (item) => {
  if (item.children) return item.children.some((c) => isPathActive(c.path))
  return isPathActive(item.path)
}
const isPathActive = (path) => {
  if (!path) return false
  return route.path === path || route.path.startsWith(path + '/')
}

const handleNav = (item, closeDrawer = false) => {
  if (item.coming) {
    ElMessage.info(`${item.label}——敬请期待`)
  } else if (item.path) {
    router.push(item.path)
  }
  if (closeDrawer) drawerOpen.value = false
}

const navigateAndClose = (path) => {
  router.push(path)
  drawerOpen.value = false
}

// ─── 用户态 ───
const displayName = computed(() => {
  try {
    const u = JSON.parse(localStorage.getItem('user') || '{}')
    return u.username || u.email || '访客'
  } catch { return '访客' }
})

const isLoggedIn = computed(() => !!localStorage.getItem('token'))

// ─── 搜索 ───
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

// ─── 其他动作 ───
const goHome = () => {
  router.push('/dashboard')
}

const handleLogout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
  drawerOpen.value = false
  router.push('/login')
}

const goUserCenter = () => {
  router.push('/user-center')
}

const goLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
/* ════════════════════════════════════════════
 * MainLayout — 全局壳层
 *   桌面顶部导航 / 移动端汉堡菜单 + drawer
 * ════════════════════════════════════════════ */

.main-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--bg-page);
}

.header {
  flex-shrink: 0;
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--sp-7);
  height: var(--header-h);
  box-shadow: var(--shadow-header);
  z-index: var(--z-header);
  position: sticky;
  top: 0;
}

.main-content {
  flex: 1;
  padding: var(--sp-6) var(--sp-7);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--sp-7);
}

.menu-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  padding: 0;
  margin-right: var(--sp-1);
  background: transparent;
  border: none;
  border-radius: var(--r-sm);
  color: var(--text-2);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}
.menu-toggle:hover,
.menu-toggle:active {
  background: var(--bg-soft-2);
}

.logo {
  font-size: 20px;
  font-weight: var(--fw-bold);
  color: var(--color-primary);
  margin: 0;
  cursor: pointer;
  letter-spacing: 0.5px;
}

.nav-menu {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.nav-item {
  padding: var(--sp-2) var(--sp-4);
  font-size: var(--fs-base);
  color: var(--text-3);
  text-decoration: none;
  border-radius: var(--r-sm);
  transition: all var(--duration-fast) var(--ease-out);
  white-space: nowrap;
}

.nav-item:hover {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.nav-item.active {
  color: var(--color-primary);
  background: var(--color-primary-soft-2);
  font-weight: var(--fw-medium);
}

/* ── 桌面二级菜单(hover 下拉)── */
.nav-dropdown {
  position: relative;
  display: inline-flex;
}
.nav-caret {
  font-size: 11px;
  margin-left: 3px;
  transition: transform var(--duration-fast) var(--ease-out);
  vertical-align: middle;
}
.nav-dropdown:hover .nav-caret {
  transform: rotate(180deg);
}
.nav-submenu {
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 132px;
  background: var(--bg-card);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-card);
  padding: var(--sp-2);
  display: flex;
  flex-direction: column;
  gap: 2px;
  opacity: 0;
  visibility: hidden;
  transform: translateY(6px);
  transition: all var(--duration-fast) var(--ease-out);
  z-index: var(--z-header);
}
/* hover 一级或下拉本身时展开;留出小桥接区避免鼠标移动断档 */
.nav-dropdown::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  height: var(--sp-3);
}
.nav-dropdown:hover .nav-submenu {
  opacity: 1;
  visibility: visible;
  transform: translateY(var(--sp-2));
}
.nav-subitem {
  padding: var(--sp-2) var(--sp-3);
  font-size: var(--fs-base);
  color: var(--text-3);
  text-decoration: none;
  border-radius: var(--r-sm);
  white-space: nowrap;
  transition: all var(--duration-fast) var(--ease-out);
}
.nav-subitem:hover {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}
.nav-subitem.active {
  color: var(--color-primary);
  background: var(--color-primary-soft-2);
  font-weight: var(--fw-medium);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--sp-4);
}

.search-wrapper {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.search-input {
  width: 0;
  opacity: 0;
  transition: all var(--duration-base) var(--ease-out);
}

.search-wrapper.expanded .search-input {
  width: 240px;
  opacity: 1;
}

.search-btn {
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: var(--r-md);
  border: none;
  background: var(--bg-page);
  color: var(--text-3);
  transition: all var(--duration-base) var(--ease-out);
}

.search-btn:hover,
.search-btn.active {
  background: var(--color-primary);
  color: #fff;
}

.search-expand-enter-active,
.search-expand-leave-active {
  transition: all var(--duration-base) var(--ease-out);
}

.search-expand-enter-from,
.search-expand-leave-to {
  width: 0;
  opacity: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  cursor: pointer;
  outline: none;
}

.user-info:hover .username {
  color: var(--color-primary);
}

.username {
  color: var(--text-3);
  font-size: var(--fs-md);
  transition: color var(--duration-fast);
}

/* 去掉 element-plus 下拉框的默认蓝色 focus 框 */
.main-layout :deep(.el-dropdown) {
  outline: none !important;
}
.main-layout :deep(.el-tooltip__trigger:focus-visible) {
  outline: none !important;
}

/* ─── 响应式 ─── */

/* < md 移动端 */
@media (max-width: 767px) {
/* 顶栏卡片化:不贴边、圆角、浮空感 */
  .header {
    /* sticky 时顶部留出 page 背景色,营造卡片在底色上漂浮的感觉 */
    position: sticky;
    top: var(--sp-3);
    /* 横向使用百分比 gutter(全面屏 4%),纵向保持固定 12px */
    margin: var(--sp-3) var(--page-gutter-mobile) 0;
    padding: 0 var(--sp-4);
    height: var(--header-h-mobile);
    border-radius: var(--r-xl);
    box-shadow: var(--shadow-card);
    /* 重要:sticky 卡片在滚动时不能让上方 dashboard 内容透出,所以给 page 底色加一层 */
  }
  .header-left {
    gap: var(--sp-3);
  }
  .username {
    display: none;
  }
  /* 移动端主内容区:横向 gutter 与 header 卡片对齐(4% 视口百分比) */
  .main-content {
    padding: var(--sp-4) var(--page-gutter-mobile) var(--sp-5);
  }
  .search-wrapper.expanded .search-input {
    width: 160px;
  }
}

/* sticky header 上方在滚动时露出 page 底色,需要在 page 顶部铺一条同色 mask 让卡片看起来"浮"在背景上 */
@media (max-width: 767px) {
  .main-layout::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: var(--sp-3);
    background: var(--bg-page);
    z-index: calc(var(--z-header) - 1);
    pointer-events: none;
  }
}

/* ════════════════════════════════════════════
 * 移动端抽屉
 * ════════════════════════════════════════════ */

.drawer-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: var(--sp-5) var(--sp-5) var(--sp-6);
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: var(--sp-5);
  border-bottom: 1px solid var(--border-light);
}

.drawer-logo {
  font-size: 22px;
  font-weight: var(--fw-bold);
  color: var(--color-primary);
  margin: 0;
  cursor: pointer;
  letter-spacing: 0.5px;
}

.drawer-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding-top: var(--sp-4);
}

.drawer-nav-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-4) var(--sp-3);
  font-size: var(--fs-lg);
  color: var(--text-2);
  text-decoration: none;
  border-radius: var(--r-md);
  transition: background var(--duration-fast) var(--ease-out);
}

.drawer-nav-item:hover,
.drawer-nav-item:active {
  background: var(--bg-soft-2);
}

.drawer-nav-item.active {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: var(--fw-medium);
}

.drawer-nav-arrow {
  color: var(--text-5);
  font-size: 14px;
}

.drawer-nav-item.active .drawer-nav-arrow {
  color: var(--color-primary);
}

/* ── 抽屉二级菜单(一级标题 + 缩进子项)── */
.drawer-group {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}
.drawer-group-label {
  padding: var(--sp-3) var(--sp-3) var(--sp-1);
  font-size: var(--fs-base);
  font-weight: var(--fw-medium);
  color: var(--text-4);
  letter-spacing: 0.5px;
}
.drawer-subitem {
  padding-left: var(--sp-5);
}

.drawer-footer {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  padding-top: var(--sp-5);
  border-top: 1px solid var(--border-light);
}

.drawer-action {
  width: 100%;
  height: var(--btn-h-lg);
  font-size: var(--fs-lg);
  border-radius: var(--r-md);
}

/* el-drawer body 去掉默认 padding */
.mobile-drawer :deep(.el-drawer__body) {
  padding: 0;
}
</style>
