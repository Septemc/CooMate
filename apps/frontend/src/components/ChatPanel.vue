<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useChatStore } from '../stores/chat'
import ChatMessage from './ChatMessage.vue'
import ChatInput from './ChatInput.vue'

const store = useChatStore()
const messagesContainer = ref<HTMLElement | null>(null)

const lastAssistantIndex = computed(() => {
  for (let i = store.messages.length - 1; i >= 0; i--) {
    if (store.messages[i].role === 'assistant') return i
  }
  return -1
})

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(() => store.messages.length, scrollToBottom)
watch(() => store.streamingContent, scrollToBottom)

function handleSend(text: string, action: string = 'chat') {
  store.sendMessage(text, action)
}
</script>

<template>
  <div class="flex flex-col flex-1 min-h-0">
    <!-- Messages -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto px-4 py-6"
    >
      <div class="max-w-3xl mx-auto">
        <!-- Empty state -->
        <div v-if="store.messages.length === 0" class="flex flex-col items-center justify-center text-center py-20" style="min-height: 60vh">
          <div class="mb-6 w-16 h-16 rounded-2xl border flex items-center justify-center" :style="{ borderColor: 'var(--border)', color: 'var(--text-primary)', boxShadow: 'var(--shadow)' }">
            <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2v4"/><path d="M12 18v4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 16.24l2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/><path d="M4.93 19.07l2.83-2.83"/><path d="M16.24 7.76l2.83-2.83"/><circle cx="12" cy="12" r="4"/>
            </svg>
          </div>
          <h2 class="text-xl font-semibold mb-2" style="color: var(--text-primary)">我是 CooMate，你的认知参谋</h2>
          <p class="text-sm max-w-md leading-relaxed mb-8" style="color: var(--text-secondary)">
            我不会直接给你答案。我会通过结构化提问，引导你自己找到答案。<br />
            说出你的困惑——情感、决策、学习、创意，都可以。
          </p>
          <div class="grid grid-cols-2 gap-3 max-w-sm w-full">
            <button
              class="shortcut-btn"
              @click="handleSend('我想研究一下这个课题的技术路线')"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <span class="text-sm font-medium" style="color: var(--text-secondary)">研究思考</span>
            </button>
            <button
              class="shortcut-btn"
              @click="handleSend('我想做一个关于AI的产品')"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1.3.5 2.6 1.5 3.5.8.8 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>
              </svg>
              <span class="text-sm font-medium" style="color: var(--text-secondary)">创意发散</span>
            </button>
            <button
              class="shortcut-btn"
              @click="handleSend('我纠结要不要分手')"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
              </svg>
              <span class="text-sm font-medium" style="color: var(--text-secondary)">情感分析</span>
            </button>
            <button
              class="shortcut-btn"
              @click="handleSend('我在纠结考研还是工作')"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
              </svg>
              <span class="text-sm font-medium" style="color: var(--text-secondary)">决策分析</span>
            </button>
          </div>
        </div>

        <!-- Message list -->
        <template v-for="(msg, idx) in store.messages" :key="msg.id">
          <ChatMessage
            :message="msg"
            :is-streaming="idx === lastAssistantIndex && store.isLoading"
            :streaming-content="idx === lastAssistantIndex ? store.streamingContent : ''"
          />
        </template>

        <!-- AI Inquiry Suggestions -->
        <div v-if="store.messages.length > 0 && !store.isLoading" class="flex items-center gap-2 mt-4 mb-2 flex-wrap">
          <button
            class="text-xs px-3 py-1.5 rounded-lg border transition-colors"
            :style="{ background: 'var(--bg-secondary)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }"
            @mouseenter="($event.target as HTMLElement).style.background = 'var(--bg-hover)'; ($event.target as HTMLElement).style.color = 'var(--text-primary)'"
            @mouseleave="($event.target as HTMLElement).style.background = 'var(--bg-secondary)'; ($event.target as HTMLElement).style.color = 'var(--text-secondary)'"
            @click="handleSend('请换个角度', 'regenerate_angles')"
          >
            ? 换个角度
          </button>
          <button
            class="text-xs px-3 py-1.5 rounded-lg border transition-colors"
            :style="{ background: 'var(--bg-secondary)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }"
            @mouseenter="($event.target as HTMLElement).style.background = 'var(--bg-hover)'; ($event.target as HTMLElement).style.color = 'var(--text-primary)'"
            @mouseleave="($event.target as HTMLElement).style.background = 'var(--bg-secondary)'; ($event.target as HTMLElement).style.color = 'var(--text-secondary)'"
            @click="handleSend('请导出复盘', 'export_review')"
          >
            ? 导出复盘
          </button>
        </div>
      </div>
    </div>

    <!-- Input -->
    <ChatInput :disabled="store.isLoading" @send="(text) => handleSend(text)" />
  </div>
</template>

<style scoped>
.shortcut-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: all var(--transition);
  text-align: left;
}
.shortcut-btn:hover {
  background: var(--bg-tertiary);
  border-color: var(--accent);
  transform: translateY(-1px);
  box-shadow: var(--shadow);
}
.shortcut-btn svg {
  flex-shrink: 0;
  color: var(--text-secondary);
}
</style>
