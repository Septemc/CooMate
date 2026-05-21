<script setup lang="ts">
import { useChatStore } from '../stores/chat'
import { computed } from 'vue'

const chatStore = useChatStore()

// We can derive the current active step based on the length of streamingSteps or the last assistant message's steps.
const currentActiveStep = computed(() => {
  if (chatStore.streamingSteps.length > 0) {
    return chatStore.streamingSteps[chatStore.streamingSteps.length - 1].step
  }
  const lastMsg = chatStore.messages[chatStore.messages.length - 1]
  if (lastMsg && lastMsg.role === 'assistant' && lastMsg.steps && lastMsg.steps.length > 0) {
    return lastMsg.steps[lastMsg.steps.length - 1].step
  }
  return 0
})

const processNodes = [
  { id: 1, title: '目标澄清', desc: '等待收集初衷', icon: 'M23 12a11 11 0 11-22 0 11 11 0 0122 0zm-11-7a7 7 0 100 14 7 7 0 000-14zm0 2a5 5 0 110 10 5 5 0 010-10zm0 2a3 3 0 100 6 3 3 0 000-6z' },
  { id: 2, title: '现状解构', desc: '梳理背景与约束', icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z' },
  { id: 3, title: '思路发散', desc: '待启动', icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z' },
  { id: 4, title: '收束决策', desc: '待启动', icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' },
]

</script>

<template>
  <aside
    class="flex-shrink-0 flex flex-col w-64 bg-sidebar border-l border-border transition-all duration-300 overflow-hidden"
  >
    <div class="p-5">
      <h2 class="text-xl font-semibold text-text-primary mb-5">思考节点</h2>
    </div>
    <div class="flex-1 overflow-y-auto px-5 pb-5">
      <ul class="relative border-l border-border ml-3 space-y-6">
        <li
          v-for="node in processNodes"
          :key="node.id"
          class="relative pl-6"
        >
          <!-- Timeline line & dot -->
          <span
            class="absolute -left-3.5 top-1 flex items-center justify-center w-7 h-7 rounded-full text-white border-2"
            :class="[
              currentActiveStep >= node.id
                ? 'bg-brand border-brand'
                : 'bg-card border-border text-text-secondary'
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" :d="node.icon" />
            </svg>
          </span>
          <!-- Content -->
          <div class="flex flex-col">
            <h4
              class="text-sm font-semibold mb-1"
              :class="currentActiveStep >= node.id ? 'text-brand' : 'text-text-primary'"
            >
              {{ node.title }}
            </h4>
            <p class="text-xs text-text-secondary">{{ node.desc }}</p>
          </div>
        </li>
      </ul>
    </div>
  </aside>
</template>
