export type ChatMode = 'chat' | 'agent' | 'plan'

export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
  request_id?: string | null
  details?: unknown
}

export interface User {
  id: number
  username: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface SessionItem {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface MessageItem {
  id: number
  role: string
  content: string
  created_at: string
}

export interface AttachmentItem {
  id: number
  message_id: number
  filename: string
  file_path: string
  file_size: number
  content_preview: string
  created_at: string
}
