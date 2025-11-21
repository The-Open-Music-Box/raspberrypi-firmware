import { createRouter, createWebHistory } from 'vue-router'
import { HomePage, AboutPage, SettingsPage } from './lazyRoutes'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: HomePage
  },
  {
    path: '/about',
    name: 'About',
    component: AboutPage
  },
  {
    path: '/settings',
    name: 'Settings',
    component: SettingsPage
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router