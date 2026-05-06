<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import {
  askInSession,
  createSession,
  deleteSession,
  getSessionMessages,
  listSessions,
  uploadChatFile,
  uploadKnowledgeBaseFile,
} from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { ChatMode, MessageItem, SessionItem } from '../types/api'

const auth = useAuthStore()

const sessions = ref<SessionItem[]>([])
const activeSessionId = ref('')
const messages = ref<MessageItem[]>([])
const inputText = ref('')
const mode = ref<ChatMode>('chat')
const sessionTitle = ref('新会话')
const sessionKeyword = ref('')
const busy = ref(false)
const assistantThinking = ref(false)
const pendingQuery = ref('')
const tip = ref('')
const sidebarOpen = ref(false)
const dragOver = ref(false)
const messagesEl = ref<HTMLElement | null>(null)

const MODE_DESC: Record<ChatMode, string> = {
  chat: '高频轻问答，直接检索增强回复',
  agent: '工具编排推理，适合复杂任务',
  plan: '生成结构化学习与执行计划',
}

const activeSession = computed(() => sessions.value.find((s) => s.id === activeSessionId.value) || null)
const filteredSessions = computed(() => {
  const key = sessionKeyword.value.trim().toLowerCase()
  if (!key) return sessions.value
  return sessions.value.filter((s) => s.title.toLowerCase().includes(key))
})
const canSend = computed(() => Boolean(activeSessionId.value && inputText.value.trim() && !busy.value))

async function loadSessions() {
  const resp = await listSessions()
  sessions.value = resp.sessions
  if (!activeSessionId.value && sessions.value.length > 0) {
    activeSessionId.value = sessions.value[0].id
    await loadMessages()
    return
  }

  if (sessions.value.length === 0) {
    const created = await createSession('新会话')
    sessions.value = [created.session]
    activeSessionId.value = created.session.id
    messages.value = []
  }
}

async function loadMessages() {
  if (!activeSessionId.value) return
  const resp = await getSessionMessages(activeSessionId.value)
  messages.value = resp.messages
}

async function createNewSession() {
  const title = sessionTitle.value.trim() || '新会话'
  const resp = await createSession(title)
  sessions.value.unshift(resp.session)
  activeSessionId.value = resp.session.id
  messages.value = []
  sessionTitle.value = '新会话'
}

async function removeSession(id: string) {
  if (!confirm('确认删除这个会话吗？')) return
  await deleteSession(id)
  if (id === activeSessionId.value) {
    activeSessionId.value = ''
    messages.value = []
  }
  await loadSessions()
}

async function sendMessage() {
  const query = inputText.value.trim()
  if (!query || !activeSessionId.value || busy.value) return

  busy.value = true
  assistantThinking.value = true
  pendingQuery.value = query
  tip.value = ''
  try {
    const resp = await askInSession(activeSessionId.value, query, mode.value)
    messages.value = resp.messages
    inputText.value = ''
    pendingQuery.value = ''
    await loadSessions()
  } catch (error: any) {
    tip.value = error?.response?.data?.message || error?.response?.data?.detail || '发送失败'
  } finally {
    assistantThinking.value = false
    busy.value = false
  }
}

function onEditorKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
    event.preventDefault()
    void sendMessage()
  }
}

async function uploadByKind(file: File, kind: 'chat' | 'kb') {
  if (!activeSessionId.value) return
  busy.value = true
  tip.value = ''

  try {
    if (kind === 'chat') {
      const resp = await uploadChatFile(activeSessionId.value, file)
      tip.value = resp.message || '会话文件上传成功'
      await loadMessages()
    } else {
      await uploadKnowledgeBaseFile(activeSessionId.value, file)
      tip.value = '知识库文件上传成功'
    }
  } catch (error: any) {
    tip.value = error?.response?.data?.message || error?.response?.data?.detail || '文件上传失败'
  } finally {
    busy.value = false
    dragOver.value = false
  }
}

async function onUploadChatFile(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  await uploadByKind(file, 'chat')
  target.value = ''
}

async function onUploadKbFile(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  await uploadByKind(file, 'kb')
  target.value = ''
}

async function onDropFile(event: DragEvent) {
  event.preventDefault()
  const file = event.dataTransfer?.files?.[0]
  if (!file) return
  await uploadByKind(file, 'chat')
}

function logout() {
  auth.clearAuth()
  location.href = '/login'
}

watch(
  () => [messages.value.length, assistantThinking.value],
  async () => {
    await nextTick()
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  },
)

onMounted(async () => {
  await auth.loadMe()
  await loadSessions()
})
</script>

<template>
  <main class="app-shell">
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="brand">
        <h2>Edu Agent</h2>
        <p>{{ auth.user?.username }}</p>
      </div>

      <input v-model="sessionKeyword" placeholder="搜索会话" class="session-search" />

      <div class="create-session">
        <input v-model="sessionTitle" placeholder="会话标题" maxlength="100" />
        <button @click="createNewSession">新建会话</button>
      </div>

      <ul class="session-list">
        <li v-for="s in filteredSessions" :key="s.id" :class="{ active: s.id === activeSessionId }">
          <button
            class="session-btn"
            @click="activeSessionId = s.id; sidebarOpen = false; loadMessages()"
          >
            <span>{{ s.title }}</span>
            <small>{{ new Date(s.updated_at).toLocaleString() }}</small>
          </button>
          <button class="danger" @click="removeSession(s.id)">删</button>
        </li>
      </ul>

      <button class="logout" @click="logout">退出登录</button>
    </aside>

    <section class="workspace">
      <header class="toolbar">
        <div class="toolbar-left">
          <button class="menu-btn" @click="sidebarOpen = !sidebarOpen">☰</button>
          <h1>{{ activeSession?.title || '请选择会话' }}</h1>
          <p>{{ MODE_DESC[mode] }}</p>
        </div>

        <div class="controls">
          <div class="mode-chips">
            <button :class="{ active: mode === 'chat' }" @click="mode = 'chat'">Chat</button>
            <button :class="{ active: mode === 'agent' }" @click="mode = 'agent'">Agent</button>
            <button :class="{ active: mode === 'plan' }" @click="mode = 'plan'">Plan</button>
          </div>

          <label class="upload-btn">
            上传会话文件
            <input type="file" @change="onUploadChatFile" />
          </label>

          <label class="upload-btn kb">
            上传知识库
            <input type="file" @change="onUploadKbFile" />
          </label>
        </div>
      </header>

      <div
        ref="messagesEl"
        class="messages"
        :class="{ 'drag-over': dragOver }"
        @dragover.prevent="dragOver = true"
        @dragleave="dragOver = false"
        @drop="onDropFile"
      >
        <article v-for="m in messages" :key="m.id" :class="['msg', m.role]">
          <div class="meta">{{ m.role }} · {{ new Date(m.created_at).toLocaleString() }}</div>
          <pre>{{ m.content }}</pre>
        </article>

        <article v-if="pendingQuery" class="msg user ghost">
          <div class="meta">user · 正在发送</div>
          <pre>{{ pendingQuery }}</pre>
        </article>

        <article v-if="assistantThinking" class="msg assistant thinking">
          <div class="meta">assistant · 思考中</div>
          <div class="dots"><span></span><span></span><span></span></div>
        </article>

        <div v-if="messages.length === 0 && !pendingQuery" class="empty-state">
          <h3>开始你的第一条消息</h3>
          <p>支持 Ctrl/Cmd + Enter 发送，或拖拽文件到此区域上传会话文件。</p>
        </div>
      </div>

      <footer class="composer">
        <div class="editor-wrap">
          <textarea
            v-model="inputText"
            placeholder="输入你的问题，回车换行，Ctrl/Cmd + Enter 发送"
            rows="3"
            @keydown="onEditorKeydown"
          ></textarea>
          <small>{{ inputText.length }}/5000</small>
        </div>
        <button :disabled="!canSend" @click="sendMessage">
          {{ busy ? '发送中...' : '发送' }}
        </button>
      </footer>

      <p v-if="tip" class="tip">{{ tip }}</p>
    </section>
  </main>
</template>
