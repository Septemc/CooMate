import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Message, StepContent, StepAnswer, StepOption } from '../types'
import { streamChat, fetchConversations, fetchConversation, deleteConversation, generateStepOptions } from '../services/api'
import type { ConversationSummary } from '../services/api'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<ConversationSummary[]>([])
  const currentConversationId = ref<string | null>(null)
  const messages = ref<Message[]>([])
  const isLoading = ref(false)
  const streamingContent = ref('')
  const streamingSteps = ref<StepContent[]>([])
  const stepOptionsLoading = ref<Record<string, boolean>>({})

  const authToken = ref<string | null>(null)
  const currentUser = ref<{ id: string; username: string; name: string; is_guest: boolean } | null>(null)

  const currentTitle = computed(() => {
    if (currentConversationId.value) {
      const conv = conversations.value.find(c => c.id === currentConversationId.value)
      return conv?.title || '新对话'
    }
    return '新对话'
  })

  const userFirstMessage = computed(() => {
    const first = messages.value.find(m => m.role === 'user')
    return first?.content || ''
  })

  function setAuth(token: string, user: { id: string; username: string; name: string; is_guest: boolean }) {
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
    stepOptionsLoading.value = {}
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
        stepAnswers: (m as any).stepAnswers || [],
        currentStep: m.steps && m.steps.length > 0 ? m.steps.length : undefined,
        isStepComplete: m.steps && m.steps.length > 0 ? true : undefined,
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

  async function fetchStepOptions(msgId: string, step: StepContent) {
    const key = `${msgId}-${step.step}`
    stepOptionsLoading.value[key] = true
    try {
      const options = await generateStepOptions(
        step.title,
        step.content,
        userFirstMessage.value,
      )
      const msg = messages.value.find(m => m.id === msgId)
      if (msg && msg.steps) {
        const targetStep = msg.steps.find(s => s.step === step.step)
        if (targetStep) {
          targetStep.options = options.map(o => ({ key: o.key, label: o.label }))
        }
      }
    } catch (e) {
      console.error('Failed to fetch step options:', e)
    } finally {
      stepOptionsLoading.value[key] = false
    }
  }

  async function prefetchAllStepOptions(msgId: string, steps: StepContent[]) {
    const validSteps = steps.filter(s => s.step > 0 && !s.options?.length)
    await Promise.all(validSteps.map(step => fetchStepOptions(msgId, step)))
  }

  async function sendMessage(text: string, action: string = 'chat', silent: boolean = false) {
    if (isLoading.value) return
    if (!text.trim()) return

    if (!silent) {
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
        timestamp: Date.now() / 1000,
      }
      messages.value.push(userMsg)
    }

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

      const hasValidSteps = finalSteps.length > 0 && finalSteps[0].step > 0

      if (hasValidSteps && action !== 'summarize') {
        assistantMsg.steps = finalSteps
        assistantMsg.currentStep = 1
        assistantMsg.isStepComplete = false
        assistantMsg.stepAnswers = []

        prefetchAllStepOptions(assistantMsg.id, finalSteps)
      } else {
        assistantMsg.content = fullText
        assistantMsg.isStepComplete = true
        if (action === 'summarize') {
          assistantMsg.isSummary = true
        }
      }

      await loadConversationList()
    } catch (err) {
      console.error('Chat error:', err)
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '抱歉，发生了错误。请检查后端服务是否运行正常。',
        timestamp: Date.now() / 1000,
        isStepComplete: true,
      }
      messages.value.push(errorMsg)
    } finally {
      isLoading.value = false
      streamingContent.value = ''
      streamingSteps.value = []
    }
  }

  function answerStep(msgId: string, stepNum: number, answer: string) {
    const msg = messages.value.find(m => m.id === msgId)
    if (!msg || !msg.steps) return

    if (!msg.stepAnswers) msg.stepAnswers = []
    const existing = msg.stepAnswers.findIndex(a => a.step === stepNum)
    if (existing >= 0) {
      msg.stepAnswers[existing].answer = answer
    } else {
      msg.stepAnswers.push({ step: stepNum, answer })
    }

    const totalSteps = msg.steps.filter(s => s.step > 0).length
    if (stepNum < totalSteps) {
      msg.currentStep = stepNum + 1
    } else {
      msg.currentStep = totalSteps + 1
      msg.isStepComplete = false
    }
  }

  function skipStep(msgId: string, stepNum: number) {
    answerStep(msgId, stepNum, '')
  }

  async function completeSupplement(msgId: string, supplement: string) {
    const msg = messages.value.find(m => m.id === msgId)
    if (!msg) return
    if (!msg.stepAnswers) msg.stepAnswers = []
    if (supplement.trim()) {
      msg.stepAnswers.push({ step: 6, answer: supplement })
    }
    msg.isStepComplete = true

    const dialogueParts: string[] = []
    if (msg.steps) {
      for (const step of msg.steps) {
        if (step.step <= 0) continue
        const ans = msg.stepAnswers.find(a => a.step === step.step)
        dialogueParts.push(`### ${step.title}

**系统提问：**
${step.content}

**用户回答：**
${ans?.answer || '（跳过）'}`)
      }
    }
    const supplementAns = msg.stepAnswers.find(a => a.step === 6)
    if (supplementAns?.answer) {
      dialogueParts.push(`### 补充

**用户补充：**
${supplementAns.answer}`)
    }

    const summaryPrompt = `你是一位认知咨询师。用户刚刚完成了一个5步结构化引导流程，以下是完整的对话记录（包含你每步的提问和用户的回答）：

${dialogueParts.join('\n\n---\n\n')}

请基于以上完整对话，生成一份深度认知复盘报告。你是咨询师，不是分析师——你要回应这个人，而不只是分析数据。

要求：

1. 使用 Markdown 格式，包含标题、小标题、表格等结构化元素

2. 报告结构如下：

## 你的核心困惑
精准概括用户真正在纠结什么。不是表面问题，是底层困惑。如果用户在回答中提出了具体问题（比如"帮我梳理触发原因"），必须在这里回应。

## 对话回顾
用表格整理每步的关键信息：

| 步骤 | 系统问了什么 | 你怎么回答的 | 值得注意的点 |
|------|-------------|-------------|-------------|
| 第一步 | ... | ... | ... |
| ... | ... | ... | ... |

"值得注意的点"这一列非常重要：如果用户在回答中提出了新问题、表达了新诉求、或者回避了什么，必须标注出来。

## 情绪模式
指出用户表现出的情绪模式（防御、逃避、循环、外化等），必须引用具体回答中的原话作为证据。如果用户提到了身体反应（如失眠、紧绷），也要分析。

## 你真正想要什么
基于用户所有回答，判断其内心真正的倾向。不是简单说"想分手"或"不想分手"，而是：在这段关系里，用户真正渴望的是什么？目前缺失的又是什么？给出判断依据。

## 未被回应的问题
如果用户在回答中提出了问题或诉求（比如"你能帮我梳理一下吗""我想先谈谈其他问题"），在这里逐一回应。这是你和用户之间的对话，不能假装没看到。

## 下一步
给出2-3个具体的、个性化的行动建议。不要泛泛而谈，要基于用户的具体情况。每个建议都要说明为什么适合这个人。

3. 语气温暖但直接，像朋友之间的认真谈话
4. 不要回避矛盾，不要和稀泥
5. 不要使用5步结构，直接输出报告
6. 内容要充实，每个板块都要有实质内容，不要一句话带过`

    await sendMessage(summaryPrompt, 'summarize', true)
  }

  function parseSteps(text: string): StepContent[] {
    const stepPattern = /\*\*第([一二三四五])步[：:]\s*(.+?)\*\*\s*(.*?)(?=\*\*第[一二三四五]步|$)/gs
    const stepMap: Record<string, number> = { '一': 1, '二': 2, '三': 3, '四': 4, '五': 5 }
    const steps: StepContent[] = []
    let match: RegExpExecArray | null
    while ((match = stepPattern.exec(text)) !== null) {
      const num = stepMap[match[1]] || 0
      let rawContent = match[3].trim()
      rawContent = rawContent.replace(/\[OPTIONS\][\s\S]*?\[\/OPTIONS\]/, '').trim()
      steps.push({
        step: num,
        title: `第${match[1]}步：${match[2].trim()}`,
        content: rawContent,
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
    stepOptionsLoading,
    currentTitle,
    authToken,
    currentUser,
    userFirstMessage,
    setAuth,
    clearAuth,
    startNewConversation,
    loadConversationList,
    loadConversation,
    removeConversation,
    sendMessage,
    answerStep,
    skipStep,
    completeSupplement,
    fetchStepOptions,
  }
})
