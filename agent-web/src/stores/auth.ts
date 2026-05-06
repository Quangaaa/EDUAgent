import { defineStore } from 'pinia'
import { fetchMe, login, register } from '../api/client'
import type { User } from '../types/api'

interface AuthState {
  token: string
  user: User | null
  loading: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('agent_token') || '',
    user: null,
    loading: false,
  }),
  getters: {
    isAuthed: (state) => Boolean(state.token),
  },
  actions: {
    setToken(token: string) {
      this.token = token
      localStorage.setItem('agent_token', token)
    },
    clearAuth() {
      this.token = ''
      this.user = null
      localStorage.removeItem('agent_token')
    },
    async doLogin(username: string, password: string) {
      this.loading = true
      try {
        const resp = await login(username, password)
        this.setToken(resp.access_token)
        this.user = resp.user
      } finally {
        this.loading = false
      }
    },
    async doRegister(username: string, password: string) {
      this.loading = true
      try {
        await register(username, password)
      } finally {
        this.loading = false
      }
    },
    async loadMe() {
      if (!this.token) return
      this.loading = true
      try {
        const resp = await fetchMe()
        this.user = resp.user
      } catch {
        this.clearAuth()
      } finally {
        this.loading = false
      }
    },
  },
})
