<template>
  <div class="panel auth-panel">
    <h1>注册</h1>
    <p class="muted">注册后即可购物、下单与个性化推荐</p>
    <form @submit.prevent="submit">
      <div class="form-row">
        <label>用户名</label>
        <input v-model="username" required minlength="2" maxlength="64" autocomplete="username" />
      </div>
      <div class="form-row">
        <label>昵称（可选）</label>
        <input v-model="nickname" maxlength="64" autocomplete="nickname" />
      </div>
      <div class="form-row">
        <label>手机号（可选）</label>
        <input v-model="telephone" maxlength="64" autocomplete="tel" />
      </div>
      <div class="form-row">
        <label>密码</label>
        <input v-model="password" type="password" required minlength="6" autocomplete="new-password" />
      </div>
      <div class="form-row">
        <label>确认密码</label>
        <input v-model="confirmPassword" type="password" required minlength="6" autocomplete="new-password" />
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="btn" type="submit" :disabled="loading">{{ loading ? '注册中...' : '注册' }}</button>
    </form>
    <p class="auth-switch muted">
      已有账号？
      <RouterLink to="/login">去登录</RouterLink>
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { register } from '@/api/mall'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()
const route = useRoute()
const username = ref('')
const nickname = ref('')
const telephone = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  if (password.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await register({
      username: username.value.trim(),
      password: password.value,
      nickname: nickname.value.trim() || undefined,
      telephone: telephone.value.trim() || undefined,
    })
    await userStore.login(username.value.trim(), password.value)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '注册失败'
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
