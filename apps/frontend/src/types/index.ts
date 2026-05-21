export interface StepContent {
  step: number
  title: string
  content: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  steps?: StepContent[]
  timestamp: number
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: number
  updatedAt: number
}

export interface ConversationSummary {
  id: string
  title: string
  updated_at: number
}

export interface StreamChunk {
  type: 'chunk' | 'done'
  content?: string
  conversation_id?: string
  steps?: StepContent[]
}
