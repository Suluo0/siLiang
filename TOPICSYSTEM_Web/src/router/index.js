import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Auth/Login.vue'),
    meta: { title: '登录', guest: true }
  },
  {
    path: '/',
    component: () => import('../layout/MainLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: '/dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard/index.vue'),
        meta: { title: '首页' }
      },
      {
        path: '/user/list',
        name: 'UserList',
        component: () => import('../views/User/List.vue'),
        meta: { title: '用户列表', requiresAdmin: true }
      },
      {
        path: '/user/level',
        name: 'UserLevel',
        component: () => import('../views/User/Level.vue'),
        meta: { title: '用户等级', requiresAdmin: true }
      },
      {
        path: '/user-center',
        name: 'UserCenter',
        component: () => import('../views/User/Center.vue'),
        meta: { title: '用户中心' }
      },
      {
        path: '/topic/library',
        name: 'TopicLibrary',
        component: () => import('../views/Topic/topic_list.vue'),
        meta: { title: '背题', guest: true }
      },
      {
        path: '/topic/practice',
        name: 'TopicPractice',
        component: () => import('../views/Topic/Practice.vue'),
        meta: { title: '刷题' }
      },
      {
        path: '/topic/detail/:id',
        name: 'TopicDetail',
        component: () => import('../views/Topic/topic_detail.vue'),
        meta: { title: '面试题详情', guest: true }
      },
      {
        path: '/skill/generate',
        name: 'SkillGenerate',
        component: () => import('../views/Skill/Generate.vue'),
        meta: { title: '技能生成' }
      },
      {
        path: '/system/menu',
        name: 'SystemMenu',
        component: () => import('../views/System/Menu.vue'),
        meta: { title: '菜单管理', requiresAdmin: true }
      },
      {
        path: '/system/permission',
        name: 'SystemPermission',
        component: () => import('../views/System/Permission.vue'),
        meta: { title: '权限管理', requiresAdmin: true }
      },
      { path: '/chat', name: 'Chat', component: () => import('../views/Chat/index.vue'), meta: { title: '对话' } },
      { path: '/interview', name: 'Interview', component: () => import('../views/Interview/index.vue'), meta: { title: '模拟面试' } },
      { path: '/privacy', name: 'Privacy', component: () => import('../views/Legal/Privacy.vue'), meta: { title: '隐私协议', guest: true } },
      { path: '/terms', name: 'Terms', component: () => import('../views/Legal/Terms.vue'), meta: { title: '用户协议', guest: true } }
    ]
  }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  const user = JSON.parse(localStorage.getItem('user') || '{}')

  // 已登录用户访问登录页 → 跳回主页
  if (to.path === '/login' && token) return '/dashboard'

  // 公开路径（游客可访问）放行
  if (to.meta.guest) return true

  // 需要管理员权限
  if (to.meta.requiresAdmin && (!user || user.membership_level !== 'admin')) {
    return '/dashboard'
  }

  // 需要登录但无 token → 跳登录
  if (to.meta.requiresAuth !== false && !token) return '/login'

  return true
})

export default router
