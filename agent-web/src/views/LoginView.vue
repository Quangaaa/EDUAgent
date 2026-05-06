<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const isRegister = ref(false)
const errorMsg = ref('')

async function submit() {
  errorMsg.value = ''
  try {
    if (isRegister.value) {
      await auth.doRegister(username.value.trim(), password.value)
      isRegister.value = false
      errorMsg.value = '注册成功，请登录。'
      return
    }

    await auth.doLogin(username.value.trim(), password.value)
    await router.push('/app')
  } catch (error: any) {
    errorMsg.value = error?.response?.data?.message || error?.response?.data?.detail || '请求失败，请检查后端是否启动。'
  }
}
</script>

<template>
  <section class="login-wrap">
    <div class="bg-grid" aria-hidden="true"></div>
    <div class="login-card">
      <h1>Edu Agent 控制台</h1>
      <p class="sub">连接你的 Chat / Agent / Plan 一体化后端</p>

      <form class="form" @submit.prevent="submit">
        <label>
          <span>用户名</span>
          <input v-model="username" required minlength="3" maxlength="64" placeholder="请输入用户名" />
        </label>

        <label>
          <span>密码</span>
          <input
            v-model="password"
            required
            minlength="6"
            maxlength="128"
            type="password"
            placeholder="请输入密码"
          />
        </label>

        <button :disabled="auth.loading" type="submit">
          {{ auth.loading ? '提交中...' : isRegister ? '注册' : '登录' }}
        </button>
      </form>

      <p class="switch">
        {{ isRegister ? '已有账号？' : '还没有账号？' }}
        <a href="#" @click.prevent="isRegister = !isRegister">{{ isRegister ? '去登录' : '去注册' }}</a>
      </p>

      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
    </div>
  </section>
</template>
