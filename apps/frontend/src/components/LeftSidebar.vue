<script setup lang="ts">
import { useChatStore } from '../stores/chat'
import { useUIStore } from '../stores/ui'
import { computed } from 'vue'
import * as api from '../services/api'

const chatStore = useChatStore()
const uiStore = useUIStore()

defineProps<{
  currentUser: { id: string; email: string; name: string; is_guest: boolean } | null
}>()

const emit = defineEmits(['openAuthModal', 'logout'])

function handleNewChat() {
  chatStore.startNewConversation()
}

function handleSelectConv(id: string) {
  chatStore.loadConversation(id)
}

function handleDeleteConv(id: string, e: Event) {
  e.stopPropagation()
  chatStore.removeConversation(id)
}

function userInitial(currentUser: any): string {
  if (!currentUser) return '?'
  return (currentUser.name || currentUser.email || '?')[0].toUpperCase()
}
</script>

<template>
  <aside
    class="sidebar flex-shrink-0 flex flex-col overflow-hidden transition-all duration-300 w-64 bg-sidebar border-r border-border"
  >
    <!-- Sidebar Header -->
    <div class="p-5 flex flex-col gap-5">
      <h2 class="text-xl font-semibold text-text-primary">CooMate</h2>
      <button
        class="w-full p-2.5 bg-card hover:bg-card-hover border border-border text-text-primary rounded-lg cursor-pointer text-[0.95rem] flex items-center justify-center gap-2 transition-colors"
        @click="handleNewChat"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        新鲜的思考
      </button>
    </div>

    <!-- Conversation List -->
    <nav class="flex-1 overflow-y-auto px-5">
      <div class="mb-2 mt-4 text-[0.75rem] text-text-secondary uppercase tracking-[0.05em]">
        最近的引导
      </div>
      <div class="space-y-1">
        <div
          v-for="conv in chatStore.conversations"
          :key="conv.id"
          class="group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors text-sm"
          :class="conv.id === chatStore.currentConversationId ? 'bg-card text-brand font-medium' : 'text-text-primary hover:bg-card-hover'"
          @click="handleSelectConv(conv.id)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 flex-shrink-0 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <span class="flex-1 truncate">{{ conv.title }}</span>
          <button
            class="opacity-0 group-hover:opacity-100 flex-shrink-0 w-5 h-5 rounded flex items-center justify-center transition-all text-text-secondary hover:text-red-500"
            @click="handleDeleteConv(conv.id, $event)"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div v-if="chatStore.conversations.length === 0" class="text-center py-4 text-xs text-text-secondary">
          暂无对话记录
        </div>
      </div>
    </nav>

    <!-- Sidebar Footer -->
    <div class="p-5 border-t border-border flex flex-col gap-4">
      <div class="flex items-center gap-2 text-text-primary">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
        </svg>
        <select
          v-model="uiStore.theme"
          @change="uiStore.setTheme(uiStore.theme)"
          class="flex-1 bg-card border border-border rounded text-sm px-2 py-1 text-text-primary focus:outline-none"
        >
          <option value="blue-white">蓝白配色 (首选)</option>
          <option value="claude">Claude经典</option>
          <option value="dark">暗色空间</option>
        </select>
      </div>

      <!-- Auth -->
      <div v-if="currentUser" class="flex gap-3 items-center group">
        <div
          class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold bg-brand text-btn-text"
        >
          {{ userInitial(currentUser) }}
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-sm font-medium truncate text-text-primary">{{ currentUser.name }}</div>
        </div>
        <button
          class="opacity-0 group-hover:opacity-100 flex-shrink-0 p-1 rounded transition-colors text-text-secondary hover:text-red-500"
          @click="$emit('logout')"
          title="退出登录"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
      </div>
      <div v-else class="flex gap-2">
        <button
          class="flex-1 px-3 py-2 rounded border border-border text-sm font-medium text-text-primary hover:bg-card-hover transition-colors"
          @click="$emit('openAuthModal', 'login')"
        >
          登录
        </button>
      </div>
    </div>
  </aside>
</template>
