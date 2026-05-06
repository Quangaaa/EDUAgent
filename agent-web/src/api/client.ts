import { http } from './http'
import type {
  ApiEnvelope,
  AttachmentItem,
  AuthResponse,
  ChatMode,
  MessageItem,
  SessionItem,
  User,
} from '../types/api'

function unwrap<T>(payload: ApiEnvelope<T>): T {
  return payload.data
}

export async function register(username: string, password: string) {
  const { data } = await http.post('/auth/register', { username, password })
  return unwrap(data as ApiEnvelope<{ user: User }>)
}

export async function login(username: string, password: string) {
  const { data } = await http.post('/auth/login', { username, password })
  return unwrap(data as ApiEnvelope<AuthResponse>)
}

export async function fetchMe() {
  const { data } = await http.get('/auth/me')
  return unwrap(data as ApiEnvelope<{ user: User }>)
}

export async function listSessions() {
  const { data } = await http.get('/chat/sessions')
  return unwrap(data as ApiEnvelope<{ sessions: SessionItem[] }>)
}

export async function createSession(title: string) {
  const { data } = await http.post('/chat/sessions', { title })
  return unwrap(data as ApiEnvelope<{ session: SessionItem }>)
}

export async function deleteSession(sessionId: string) {
  const { data } = await http.delete(`/chat/sessions/${sessionId}`)
  return unwrap(data as ApiEnvelope<{ history_deleted: boolean }>)
}

export async function getSessionMessages(sessionId: string) {
  const { data } = await http.get(`/chat/sessions/${sessionId}/messages`)
  return unwrap(data as ApiEnvelope<{
    messages: MessageItem[]
    attachments: AttachmentItem[]
  }>)
}

export async function askInSession(sessionId: string, query: string, mode: ChatMode) {
  const { data } = await http.post(`/chat/sessions/${sessionId}/ask`, { query, mode })
  return unwrap(data as ApiEnvelope<{
    session_id: string
    mode: ChatMode
    answer: string
    messages: MessageItem[]
  }>)
}

export async function uploadChatFile(sessionId: string, file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await http.post(`/chat/sessions/${sessionId}/upload`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data as ApiEnvelope<{
    session_id: string
    filename: string
    size: number
    stored_in: string
    kb_result: unknown
  }>
}

export async function uploadKnowledgeBaseFile(sessionId: string, file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await http.post(`/knowledgebase/kb/upload`, fd, {
    params: { session_id: sessionId },
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return unwrap(data as ApiEnvelope<{ kb_result: unknown }>)
}
