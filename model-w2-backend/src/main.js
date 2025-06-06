import './assets/main.css'
import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Login from './components/Login.vue'
import UserDashboard from './components/UserDashboard.vue'
import AdminDashboard from './components/AdminDashboard.vue'

const routes = [
  { path: '/', component: Login },
  { path: '/user', component: UserDashboard },
  { path: '/admin', component: AdminDashboard }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 添加全局前置守卫
router.beforeEach((to, from, next) => {
    // 如果访问根路径，清除用户数据
    if (to.path === '/') {
      localStorage.removeItem('user')
    }
    
    // 检查认证状态
    const user = localStorage.getItem('user')
    if (to.path !== '/' && !user) {
      // 如果访问需要认证的页面但没有登录，重定向到登录页
      next('/')
    } else {
      next()
    }
  })
  

const app = createApp(App)
app.use(router)
app.mount('#app')