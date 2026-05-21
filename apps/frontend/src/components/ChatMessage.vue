<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import type { Message } from '../types'
import StepSection from './StepSection.vue'

const props = defineProps<{
  message: Message
  streamingContent?: string
  isStreaming?: boolean
}>()

const isUser = computed(() => props.message.role === 'user')

const displaySteps = computed(() => {
  if (props.message.steps?.length) return props.message.steps
  return null
})

const renderStreamingContent = computed(() => {
  return marked.parse(props.streamingContent || '', { breaks: true }) as string
})

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {})
}
</script>

<template>
  <div class="chat-message" :class="isUser ? 'msg-user' : 'msg-ai'">
    <div class="message-content w-full">
      <!-- User text -->
      <template v-if="isUser">
        {{ message.content }}
      </template>
      
      <!-- AI content -->
      <template v-else>
        <!-- Rendered steps -->
        <template v-if="displaySteps && !isStreaming">
          <StepSection
            v-for="s in displaySteps"
            :key="s.step"
            :step="s"
          />
          <div v-if="!displaySteps.length" class="whitespace-pre-wrap leading-relaxed">
            {{ message.content }}
          </div>
        </template>

        <!-- Streaming raw content -->
        <div v-else-if="isStreaming">
          <!-- Thinking indicator with bouncing dots -->
          <div v-if="!streamingContent" class="flex items-center gap-3 py-4">
            <div class="thinking-dots">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
            <span class="text-sm text-text-secondary animate-pulse">CooMate 正在思考</span>
          </div>
          <!-- Streaming content -->
          <div v-else>
            <div
              class="leading-relaxed whitespace-pre-wrap streaming-cursor step-content"
              v-html="renderStreamingContent"
            />
          </div>
        </div>

        <!-- Fallback raw content -->
        <div v-else class="leading-relaxed whitespace-pre-wrap">
          {{ message.content }}
        </div>
      </template>
    </div>

    <!-- Actions (User) -->
    <div v-if="isUser" class="message-actions user-actions mt-2 text-text-muted flex gap-2">
      <button class="action-btn" title="复制" @click="copyToClipboard(message.content)">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
      </button>
      <button class="action-btn" title="编辑">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
      </button>
    </div>

    <!-- Actions (AI) -->
    <div v-if="!isUser && (!isStreaming || (isStreaming && !streamingContent))" class="message-actions ai-actions mt-2 text-text-muted flex gap-2">
      <button class="action-btn" title="复制" @click="copyToClipboard(message.content)">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
      </button>
      <button class="action-btn" title="有帮助">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"/></svg>
      </button>
      <button class="action-btn" title="无帮助">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"/></svg>
      </button>
      <button class="action-btn" title="重新生成">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
/* Thinking dots animation */
.thinking-dots {
  display: flex;
  align-items: center;
  gap: 6px;
}

.thinking-dots .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: var(--accent, #10a37f);
  animation: dot-bounce 1.4s infinite ease-in-out both;
}

.thinking-dots .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.thinking-dots .dot:nth-child(2) {
  animation-delay: -0.16s;
}

.thinking-dots .dot:nth-child(3) {
  animation-delay: 0s;
}

@keyframes dot-bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* Streaming cursor */
.streaming-cursor::after {
  content: '▋';
  display: inline;
  animation: blink 0.7s infinite;
  color: var(--accent, #10a37f);
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* Step content styling */
.step-content :deep(p) {
  margin-bottom: 0.5rem;
}

.step-content :deep(strong) {
  color: var(--text-primary, #ececec);
}
</style>
