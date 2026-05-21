<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  send: [text: string]
}>()

defineProps<{
  disabled?: boolean
}>()

const text = ref('')

function handleSend() {
  const trimmed = text.value.trim()
  if (!trimmed) return
  emit('send', trimmed)
  text.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function autoResize(e: Event) {
  const el = e.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}
</script>

<template>
  <div
    class="flex-shrink-0 px-4 py-3"
    :style="{ borderTop: '1px solid var(--border)', background: 'var(--bg-primary)' }"
  >
    <div class="max-w-3xl mx-auto flex gap-3 items-end">
      <textarea
        v-model="text"
        :disabled="disabled"
        placeholder="说出你的困惑，我来引导你思考..."
        rows="1"
        class="flex-1 px-4 py-3 text-sm resize-none outline-none rounded-xl transition-colors"
        :style="{
          background: 'var(--bg-input)',
          border: '1px solid var(--border)',
          color: 'var(--text-primary)',
          minHeight: '44px',
          maxHeight: '200px',
          fontFamily: 'inherit',
          lineHeight: '1.5',
        }"
        @focus="($event.target as HTMLElement).style.borderColor = 'var(--accent)'; ($event.target as HTMLElement).style.boxShadow = '0 0 0 3px rgba(37,99,235,0.1)'"
        @blur="($event.target as HTMLElement).style.borderColor = 'var(--border)'; ($event.target as HTMLElement).style.boxShadow = 'none'"
        @input="autoResize"
        @keydown="handleKeydown"
      />
      <button
        :disabled="disabled || !text.trim()"
        class="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-colors text-white"
        :style="{
          background: disabled || !text.trim() ? 'var(--text-muted)' : 'var(--accent)',
          cursor: disabled || !text.trim() ? 'not-allowed' : 'pointer',
          opacity: disabled || !text.trim() ? '0.4' : '1',
        }"
        @click="handleSend"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M12 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  </div>
</template>
