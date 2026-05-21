import type { StreamChunk } from '../types'

const BASE = '/api'

// --- Auth helpers ---
function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('coomate-token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

// --- Stream Chat ---
export async function* streamChat(
  message: string,
  conversationId?: string,
  action: string = 'chat',
): AsyncGenerator<StreamChunk> {
  const resp = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      action,
    }),
  })

  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}: ${resp.statusText}`)
  }

  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed || !trimmed.startsWith('data: ')) continue
      try {
        const chunk: StreamChunk = JSON.parse(trimmed.slice(6))
        yield chunk
      } catch {
        // skip malformed lines
      }
    }
  }
}

// --- Conversation APIs ---
export interface ConversationSummary {
  id: string
  title: string
  updated_at: number
}

export interface ConversationDetail {
  id: string
  title: string
  messages: Array<{
    id: string
    role: string
    content: string
    steps?: Array<{ step: number; title: string; content: string }>
    timestamp: number
  }>
  created_at: number
  updated_at: number
}

export async function fetchConversations(): Promise<ConversationSummary[]> {
  const resp = await fetch(`${BASE}/conversations`, { headers: getAuthHeaders() })
  return resp.json()
}

export async function fetchConversation(id: string): Promise<ConversationDetail> {
  const resp = await fetch(`${BASE}/conversations/${id}`, { headers: getAuthHeaders() })
  return resp.json()
}

export async function deleteConversation(id: string): Promise<void> {
  await fetch(`${BASE}/conversations/${id}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  })
}

// --- Auth APIs ---
export interface AuthResponse {
  token: string
  user: {
    id: string
    email: string
    name: string
    is_guest: boolean
  }
}

export async function register(email: string, password: string, name?: string): Promise<AuthResponse> {
  const resp = await fetch(`${BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, name }),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Registration failed' }))
    throw new Error(err.detail || 'Registration failed')
  }
  return resp.json()
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const resp = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Login failed' }))
    throw new Error(err.detail || 'Login failed')
  }
  return resp.json()
}

export async function guestLogin(): Promise<AuthResponse> {
  const resp = await fetch(`${BASE}/auth/guest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!resp.ok) throw new Error('Guest login failed')
  return resp.json()
}

export async function logout(): Promise<void> {
  await fetch(`${BASE}/auth/logout`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })
}
