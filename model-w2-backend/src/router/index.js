import Vue from 'vue'
import VueRouter from 'vue-router'
import Login from '../components/Login.vue'
import UserDashboard from '../components/UserDashboard.vue'
import AdminDashboard from '../components/AdminDashboard.vue'
Vue.use(VueRouter)

const routes = [
  {
    path:' /login',
    name: 'Login',
    component:Login
  },{
    path: '/user',
    name: 'UserDashboard',
    component: UserDashboard
  },
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: AdminDashboard
  }
]

const router = new VueRouter({
  mode: 'history',
  routes
})

export default router