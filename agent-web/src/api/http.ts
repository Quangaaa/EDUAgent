import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export const http = axios.create({
  baseURL,
  timeout: 20000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('agent_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
