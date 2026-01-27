import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import WorkView from '../views/WorkView.vue'
import { useAuth } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView },
    { path: '/', name: 'work', component: WorkView, meta: { requiresAuth: true } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const { isAuthed } = useAuth()
  if (to.meta.requiresAuth && !isAuthed()) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  if (to.name === 'login' && isAuthed()) {
    return { name: 'work' }
  }
  return true
})

export default router