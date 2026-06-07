import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchMemberInfo, login as loginApi } from '@/api/mall'

export const useUserStore = defineStore(
  'user',
  () => {
    const token = ref('')
    const username = ref('')
    const nickname = ref('')

    async function login(user: string, password: string) {
      const res = await loginApi(user, password)
      const data = res.data as { token: string; tokenHead: string }
      token.value = data.tokenHead + data.token
      username.value = user
      const info = await fetchMemberInfo()
      nickname.value = (info.data as { nickname?: string }).nickname || user
    }

    function logout() {
      token.value = ''
      username.value = ''
      nickname.value = ''
    }

    return { token, username, nickname, login, logout }
  },
  { persist: true },
)
