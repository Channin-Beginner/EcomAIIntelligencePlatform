import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
    { path: '/search', name: 'search', component: () => import('@/views/SearchView.vue') },
    { path: '/product/:id', name: 'product', component: () => import('@/views/ProductDetailView.vue') },
    { path: '/brand/:id', name: 'brand', component: () => import('@/views/BrandView.vue') },
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
    { path: '/register', name: 'register', component: () => import('@/views/RegisterView.vue') },
    { path: '/favorites', name: 'favorites', component: () => import('@/views/FavoritesView.vue'), meta: { auth: true } },
    { path: '/cart', name: 'cart', component: () => import('@/views/CartView.vue'), meta: { auth: true } },
    { path: '/checkout', name: 'checkout', component: () => import('@/views/CheckoutView.vue'), meta: { auth: true } },
    { path: '/orders', name: 'orders', component: () => import('@/views/OrderListView.vue'), meta: { auth: true } },
  ],
})

router.beforeEach(to => {
  if (to.meta.auth && !useUserStore().token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})

export default router
