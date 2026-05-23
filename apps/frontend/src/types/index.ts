export interface StepOption {
  key: string
  label: string
}

export interface StepContent {
  step: number
  title: string
  content: string
  options?: StepOption[]
}

export interface StepAnswer {
  step: number
  answer: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  steps?: StepContent[]
  stepAnswers?: StepAnswer[]
  currentStep?: number
  isStepComplete?: boolean
  isSummary?: boolean
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
