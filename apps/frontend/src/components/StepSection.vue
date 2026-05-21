<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import type { StepContent } from '../types'

const props = defineProps<{
  step: StepContent
  streaming?: boolean
}>()

const stepStyles: Record<number, { bg: string; border: string; badge: string }> = {
  1: { bg: 'var(--step-1-bg)', border: 'var(--step-1-border)', badge: 'var(--step-1)' },
  2: { bg: 'var(--step-2-bg)', border: 'var(--step-2-border)', badge: 'var(--step-2)' },
  3: { bg: 'var(--step-3-bg)', border: 'var(--step-3-border)', badge: 'var(--step-3)' },
  4: { bg: 'var(--step-4-bg)', border: 'var(--step-4-border)', badge: 'var(--step-4)' },
  5: { bg: 'var(--step-5-bg)', border: 'var(--step-5-border)', badge: 'var(--step-5)' },
  0: { bg: 'var(--bg-secondary)', border: 'var(--border)', badge: 'var(--text-muted)' },
}

const colors = computed(() => stepStyles[props.step.step] || stepStyles[0])

const renderedContent = computed(() => {
  return marked.parse(props.step.content || '', { breaks: true }) as string
})
</script>

<template>
  <div
    class="step-card rounded-lg border p-4 mb-3"
    :style="{
      background: colors.bg,
      borderColor: colors.border,
      boxShadow: 'var(--shadow)',
    }"
  >
    <div class="flex items-center gap-2 mb-2">
      <span
        class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold text-white flex-shrink-0"
        :style="{ background: colors.badge }"
      >
        {{ step.step || '?' }}
      </span>
      <h3 class="text-sm font-semibold" style="color: var(--text-primary)">{{ step.title }}</h3>
    </div>
    <div
      class="step-content text-sm leading-relaxed"
      :class="{ 'streaming-cursor': streaming }"
      style="color: var(--text-secondary)"
      v-html="renderedContent"
    />
  </div>
</template>
