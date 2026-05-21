import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Message, StepContent } from '../types'
import { streamChat, fetchConversations, fetchConversation, deleteConversation } from '../services/api'
import type { ConversationSummary } from '../services/api'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<ConversationSummary[]>([])
  const currentConversationId = ref<string | null>(null)
  const messages = ref<Message[]>([])
  const isLoading = ref(false)
  const streamingContent = ref('')
  const streamingSteps = ref<StepContent[]>([])

  // Auth state
  const authToken = ref<string | null>(null)
  const currentUser = ref<{ id: string; email: string; name: string; is_guest: boolean } | null>(null)

  const currentTitle = computed(() => {
    if (currentConversationId.value) {
      const conv = conversations.value.find(c => c.id === currentConversationId.value)
      return conv?.title || '新对话'
    }
    return '新对话'
  })

  function setAuth(token: string, user: { id: string; email: string; name: string; is_guest: boolean }) {
    authToken.value = token
    currentUser.value = user
  }

  function clearAuth() {
    authToken.value = null
    currentUser.value = null
    conversations.value = []
    startNewConversation()
  }

  function startNewConversation() {
    currentConversationId.value = null
    messages.value = []
    streamingContent.value = ''
    streamingSteps.value = []
  }

  async function loadConversationList() {
    try {
      conversations.value = await fetchConversations()
    } catch (e) {
      console.error('Failed to load conversations:', e)
    }
  }

  async function loadConversation(id: string) {
    try {
      const conv = await fetchConversation(id)
      currentConversationId.value = conv.id
      messages.value = conv.messages.map(m => ({
        id: m.id,
        role: m.role as 'user' | 'assistant',
        content: m.content,
        steps: m.steps,
        timestamp: m.timestamp,
      }))
    } catch (e) {
      console.error('Failed to load conversation:', e)
    }
  }

  async function removeConversation(id: string) {
    try {
      await deleteConversation(id)
      conversations.value = conversations.value.filter(c => c.id !== id)
      if (currentConversationId.value === id) {
        startNewConversation()
      }
    } catch (e) {
      console.error('Failed to delete conversation:', e)
    }
  }

  async function sendMessage(text: string, action: string = 'chat') {
    if (isLoading.value) return
    if (!text.trim()) return

    // Add user message
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: Date.now() / 1000,
    }
    messages.value.push(userMsg)

    isLoading.value = true
    streamingContent.value = ''
    streamingSteps.value = []

    const assistantMsg: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      timestamp: Date.now() / 1000,
    }
    messages.value.push(assistantMsg)

    try {
      let fullText = ''
      let finalSteps: StepContent[] = []
      let convId = currentConversationId.value || undefined

      for await (const chunk of streamChat(text, convId, action)) {
        if (chunk.type === 'chunk' && chunk.content) {
          fullText += chunk.content
          streamingContent.value = fullText
          assistantMsg.content = fullText
        }
        if (chunk.type === 'done') {
          finalSteps = chunk.steps || []
          if (chunk.conversation_id) {
            convId = chunk.conversation_id
            currentConversationId.value = convId
          }
        }
      }

      if (!finalSteps.length) {
        finalSteps = parseSteps(fullText)
      }

      assistantMsg.steps = finalSteps

      await loadConversationList()
    } catch (err) {
      console.error('Chat error:', err)
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '抱歉，发生了错误。请检查后端服务是否运行正常。',
        timestamp: Date.now() / 1000,
      }
      messages.value.push(errorMsg)
    } finally {
      isLoading.value = false
      streamingContent.value = ''
      streamingSteps.value = []
    }
  }

  function parseSteps(text: string): StepContent[] {
    const stepPattern = /\*\*第([一二三四五])步[：:]\s*(.+?)\*\*\s*(.*?)(?=\*\*第[一二三四五]步|$)/gs
    const stepMap: Record<string, number> = { '一': 1, '二': 2, '三': 3, '四': 4, '五': 5 }
    const steps: StepContent[] = []
    let match: RegExpExecArray | null
    while ((match = stepPattern.exec(text)) !== null) {
      const num = stepMap[match[1]] || 0
      steps.push({
        step: num,
        title: `第${match[1]}步：${match[2].trim()}`,
        content: match[3].trim(),
      })
    }
    if (!steps.length) {
      steps.push({ step: 0, title: '回复', content: text })
    }
    return steps
  }

  return {
    conversations,
    currentConversationId,
    messages,
    isLoading,
    streamingContent,
    streamingSteps,
    currentTitle,
    authToken,
    currentUser,
    setAuth,
    clearAuth,
    startNewConversation,
    loadConversationList,
    loadConversation,
    removeConversation,
    sendMessage,
  }
})
