import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'

const routes = [
  { 
    path: '/login', 
    name: 'Login', 
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/tts-test',
    name: 'TTSTest',
    component: () => import('@/views/TTSTest.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/',
    component: () => import('@/views/Home.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/step/1' },
      { path: 'step/1', name: 'StepCreate', component: () => import('@/views/StepCreate.vue') },
      { path: 'step/2', name: 'StepCharacter', component: () => import('@/views/StepCharacter.vue') },
      { path: 'step/3', name: 'StepStoryboard', component: () => import('@/views/StepStoryboard.vue') },
      { path: 'step/4', name: 'StepEdit', component: () => import('@/views/StepEdit.vue') },
      { path: 'step/5', name: 'StepAudio', component: () => import('@/views/StepAudio.vue') },
      { path: 'step/6', name: 'StepExport', component: () => import('@/views/StepExport.vue') },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  const projectStore = useProjectStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else {
    // 已登录且未初始化项目数据时，尝试从 localStorage 恢复
    if (authStore.isAuthenticated && !projectStore.initialized) {
      await projectStore.initFromStorage()
    }
    next()
  }
})

export default router
