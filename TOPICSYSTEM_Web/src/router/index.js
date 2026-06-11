import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Auth/Login.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/',
    component: () => import('../layout/MainLayout.vue'),
    redirect: '/dashboard',
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
        meta: { title: '用户列表' }
      },
      {
        path: '/user/level',
        name: 'UserLevel',
        component: () => import('../views/User/Level.vue'),
        meta: { title: '用户等级' }
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
        meta: { title: '题库' }
      },
      {
        path: '/topic/detail/:id',
        name: 'TopicDetail',
        component: () => import('../views/Topic/topic_detail.vue'),
        meta: { title: '面试题详情' }
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
        meta: { title: '菜单管理' }
      },
      {
        path: '/system/permission',
        name: 'SystemPermission',
        component: () => import('../views/System/Permission.vue'),
        meta: { title: '权限管理' }
      },
      {
        path: '/chat',
        name: 'Chat',
        component: () => import('../views/Chat/index.vue'),
        meta: { title: '对话' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫 — 未登录跳到 /login
router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (!token && to.path !== '/login') {
    return '/login'
  }
})

export default router
