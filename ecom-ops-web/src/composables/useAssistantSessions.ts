import { computed, ref } from 'vue'
import type { AssistantQueryResult } from '@/api/assistant'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  loading?: boolean
  result?: AssistantQueryResult
}

export interface ChatSession {
  id: string
  title: string
  pinned: boolean
  messages: ChatMessage[]
  updatedAt: number
}

const STORAGE_KEY = 'ecomai-assistant-sessions'

function loadSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as ChatSession[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function saveSessions(list: ChatSession[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
}

function sortSessions(list: ChatSession[]): ChatSession[] {
  return [...list].sort((a, b) => {
    if (a.pinned !== b.pinned) return a.pinned ? -1 : 1
    return b.updatedAt - a.updatedAt
  })
}

function titleFromQuestion(q: string): string {
  const t = q.trim().replace(/\s+/g, ' ')
  return t.length > 18 ? `${t.slice(0, 18)}…` : t || '新对话'
}

export function useAssistantSessions() {
  const sessions = ref<ChatSession[]>(sortSessions(loadSessions()))
  const activeSessionId = ref<string | null>(null)
  const messages = ref<ChatMessage[]>([])

  const sortedSessions = computed(() => sortSessions(sessions.value))

  const activeTitle = computed(() => {
    if (!activeSessionId.value) return '新对话'
    return sessions.value.find(s => s.id === activeSessionId.value)?.title ?? '新对话'
  })

  function persistActive() {
    if (!activeSessionId.value || messages.value.length === 0) return
    const idx = sessions.value.findIndex(s => s.id === activeSessionId.value)
    const payload: ChatSession = {
      id: activeSessionId.value,
      title:
        idx >= 0
          ? sessions.value[idx].title
          : titleFromQuestion(messages.value.find(m => m.role === 'user')?.text ?? '新对话'),
      pinned: idx >= 0 ? sessions.value[idx].pinned : false,
      messages: messages.value.filter(m => !m.loading),
      updatedAt: Date.now(),
    }
    if (idx >= 0) {
      sessions.value[idx] = payload
    } else {
      sessions.value.unshift(payload)
    }
    sessions.value = sortSessions(sessions.value)
    saveSessions(sessions.value)
  }

  function startNewChat() {
    persistActive()
    activeSessionId.value = null
    messages.value = []
  }

  function ensureSession(firstQuestion: string): string {
    if (activeSessionId.value) return activeSessionId.value
    const id = `s-${Date.now()}`
    activeSessionId.value = id
    const session: ChatSession = {
      id,
      title: titleFromQuestion(firstQuestion),
      pinned: false,
      messages: [],
      updatedAt: Date.now(),
    }
    sessions.value = sortSessions([session, ...sessions.value])
    saveSessions(sessions.value)
    return id
  }

  function selectSession(id: string) {
    if (id === activeSessionId.value) return
    persistActive()
    const session = sessions.value.find(s => s.id === id)
    if (!session) return
    activeSessionId.value = id
    messages.value = [...session.messages]
  }

  function togglePin(id: string) {
    const s = sessions.value.find(x => x.id === id)
    if (!s) return
    s.pinned = !s.pinned
    s.updatedAt = Date.now()
    sessions.value = sortSessions(sessions.value)
    saveSessions(sessions.value)
  }

  function renameSession(id: string, title: string) {
    const t = title.trim()
    if (!t) return
    const s = sessions.value.find(x => x.id === id)
    if (!s) return
    s.title = t
    s.updatedAt = Date.now()
    sessions.value = sortSessions(sessions.value)
    saveSessions(sessions.value)
  }

  function deleteSession(id: string) {
    sessions.value = sessions.value.filter(s => s.id !== id)
    saveSessions(sessions.value)
    if (activeSessionId.value === id) {
      activeSessionId.value = null
      messages.value = []
    }
  }

  function touchActive() {
    persistActive()
  }

  return {
    sessions: sortedSessions,
    activeSessionId,
    messages,
    activeTitle,
    startNewChat,
    ensureSession,
    selectSession,
    togglePin,
    renameSession,
    deleteSession,
    touchActive,
  }
}
