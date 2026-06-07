import axios from 'axios'

export interface CommonResult<T = unknown> {
  code: number
  message: string
  data: T
}

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 20000,
})

http.interceptors.response.use(response => {
  const res = response.data as CommonResult
  if (res.code !== 200) {
    return Promise.reject(new Error(res.message || '请求失败'))
  }
  return response.data
})

export default http
