<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: number | string;
    strokeWidth?: number;
    framed?: boolean;
    animated?: boolean;
  }>(),
  {
    size: 20,
    strokeWidth: 1.8,
    framed: false,
    animated: false
  }
);
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <rect
      v-if="framed"
      x="3.25"
      y="4.25"
      width="17.5"
      height="15.5"
      rx="3.25"
      stroke="currentColor"
      :stroke-width="strokeWidth"
      opacity="0.72"
    />
    <path
      d="M8 9.5L11.5 12L8 14.5"
      stroke="currentColor"
      :stroke-width="strokeWidth"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <path
      d="M13.5 15.25H17.25"
      stroke="currentColor"
      :stroke-width="strokeWidth"
      stroke-linecap="round"
      :class="{ cursor: animated }"
    />
  </svg>
</template>

<style scoped>
.cursor {
  animation: blink 1.15s steps(2, jump-none) infinite;
}

@keyframes blink {
  0%,
  48% {
    opacity: 1;
  }

  52%,
  100% {
    opacity: 0.28;
  }
}
</style>
