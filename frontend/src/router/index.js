import { createRouter, createWebHashHistory } from 'vue-router'
import Signals from '../views/Signals.vue'
import Portfolio from '../views/Portfolio.vue'
import Assets from '../views/Assets.vue'
import TaskLogs from '../views/TaskLogs.vue'

const routes = [
  {
    path: '/',
    redirect: '/signals'
  },
  {
    path: '/signals',
    name: 'Signals',
    component: Signals,
    meta: { title: '今日信号', icon: 'Bell' }
  },
  {
    path: '/portfolio',
    name: 'Portfolio',
    component: Portfolio,
    meta: { title: '持仓管理', icon: 'Wallet' }
  },
  {
    path: '/assets',
    name: 'Assets',
    component: Assets,
    meta: { title: '资产走势', icon: 'TrendCharts' }
  },
  {
    path: '/logs',
    name: 'TaskLogs',
    component: TaskLogs,
    meta: { title: '任务日志', icon: 'List' }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export { routes }
export default router
