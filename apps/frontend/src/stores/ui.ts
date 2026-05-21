import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUIStore = defineStore('ui', () => {
  // --- Theme ---
  const savedTheme = localStorage.getItem('coomate-theme') || 'blue-white'
  const theme = ref<'blue-white' | 'claude' | 'dark'>(savedTheme as any)

  function setTheme(newTheme: 'blue-white' | 'claude' | 'dark') {
    theme.value = newTheme
    localStorage.setItem('coomate-theme', newTheme)
    
    // Apply classes to body
    document.body.classList.remove('theme-claude', 'theme-dark')
    if (newTheme === 'claude') document.body.classList.add('theme-claude')
    if (newTheme === 'dark') document.body.classList.add('theme-dark')
    // Set data-theme for any legacy code
    document.documentElement.setAttribute('data-theme', newTheme === 'dark' ? 'dark' : 'light')
  }

  // Initial apply
  setTheme(theme.value)

  // --- Sidebars ---
  const leftSidebarOpen = ref(localStorage.getItem('coomate-left-sidebar') !== 'closed')
  const rightSidebarOpen = ref(localStorage.getItem('coomate-right-sidebar') !== 'closed')

  function toggleLeftSidebar() {
    leftSidebarOpen.value = !leftSidebarOpen.value
    localStorage.setItem('coomate-left-sidebar', leftSidebarOpen.value ? 'open' : 'closed')
  }

  function toggleRightSidebar() {
    rightSidebarOpen.value = !rightSidebarOpen.value
    localStorage.setItem('coomate-right-sidebar', rightSidebarOpen.value ? 'open' : 'closed')
  }

  // --- Agent Inquiry Mode (Suggestions Bar) ---
  const isAgentAsking = ref(false)
  const agentSuggestions = ref<{ label: string; text: string }[]>([])

  function setAgentInquiry(suggestions: { label: string; text: string }[]) {
    isAgentAsking.value = true
    agentSuggestions.value = suggestions
  }

  function clearAgentInquiry() {
    isAgentAsking.value = false
    agentSuggestions.value = []
  }

  return {
    theme,
    setTheme,
    leftSidebarOpen,
    rightSidebarOpen,
    toggleLeftSidebar,
    toggleRightSidebar,
    isAgentAsking,
    agentSuggestions,
    setAgentInquiry,
    clearAgentInquiry,
  }
})
