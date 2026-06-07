<template>
  <div class="panel auth-panel">
    <h1>登录</h1>
    <p class="muted">默认账号 test / 123456（需已导入 mall.sql）</p>
    <form @submit.prevent="submit">
      <div class="form-row">
        <label>用户名</label>
        <input v-model="username" required autocomplete="username" />
      </div>
      <div class="form-row">
        <label>密码</label>
        <input v-model="password" type="password" required autocomplete="current-password" />
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="btn" type="submit" :disabled="loading">{{ loading ? '登录中...' : '登录' }}</button>
    </form>
    <p class="auth-switch muted">
      还没有账号？
      <RouterLink :to="{ name: 'register', query: route.query }">去注册</RouterLink>
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()
const route = useRoute()
const username = ref('test')
const password = ref('123456')
const error = ref('')
const loading = ref(false)

async function submit() {
  loading.value = true
  error.value = ''
  try {
    await userStore.login(username.value, password.value)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-panel {
  max-width: 420px;
  margin: 40px auto;
}

.auth-switch {
  margin-top: 16px;
  text-align: center;
}

.auth-switch a {
  color: var(--primary);
}
</style>
