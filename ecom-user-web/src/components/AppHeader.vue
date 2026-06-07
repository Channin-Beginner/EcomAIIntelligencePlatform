<template>
  <header class="header">
    <div class="header-inner">
      <div class="header-left">
        <RouterLink to="/" class="logo">EcomAI Mall</RouterLink>
        <form class="search-form" @submit.prevent="onSearch">
          <input v-model="keyword" placeholder="搜索商品" />
          <button type="submit">搜索</button>
        </form>
      </div>
      <nav class="header-right nav-links">
        <RouterLink to="/favorites">我的收藏</RouterLink>
        <RouterLink to="/cart">购物车</RouterLink>
        <RouterLink to="/orders">我的订单</RouterLink>
        <template v-if="userStore.token">
          <span class="user-name">{{ userStore.nickname || userStore.username }}</span>
          <button type="button" class="link-btn" @click="logout">退出</button>
        </template>
        <template v-else>
          <RouterLink to="/login">登录</RouterLink>
          <RouterLink to="/register">注册</RouterLink>
        </template>
      </nav>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const keyword = ref('')

function onSearch() {
  router.push({ name: 'search', query: { keyword: keyword.value } })
}

function logout() {
  userStore.logout()
  router.push('/')
}
</script>
