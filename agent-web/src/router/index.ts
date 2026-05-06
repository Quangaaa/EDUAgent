import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import ChatView from '../views/ChatView.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/app' },
    { path: '/login', component: LoginView },
    { path: '/app', component: ChatView },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (auth.token && !auth.user) {
    await auth.loadMe()
  }

  if (to.path !== '/login' && !auth.isAuthed) {
    return '/login'
  }

  if (to.path === '/login' && auth.isAuthed) {
    return '/app'
  }

  return true
})

export default router
