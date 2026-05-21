<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useChatStore } from './stores/chat'
import { useUIStore } from './stores/ui'
import ChatPanel from './components/ChatPanel.vue'
import LeftSidebar from './components/LeftSidebar.vue'
import RightSidebar from './components/RightSidebar.vue'
import * as api from './services/api'

const store = useChatStore()
const uiStore = useUIStore()

// --- Auth ---
const showAuthModal = ref(false)
const authMode = ref<'login' | 'register'>('login')
const authEmail = ref('')
const authPassword = ref('')
const authName = ref('')
const authLoading = ref(false)
const authError = ref('')

function openAuthModal(mode: 'login' | 'register') {
  authMode.value = mode
  authEmail.value = ''
  authPassword.value = ''
  authName.value = ''
  authError.value = ''
  showAuthModal.value = true
}

function closeAuthModal() {
  showAuthModal.value = false
}

async function handleAuth() {
  authError.value = ''
  authLoading.value = true
  try {
    let resp: api.AuthResponse
    if (authMode.value === 'register') {
      resp = await api.register(authEmail.value, authPassword.value, authName.value || undefined)
    } else {
      resp = await api.login(authEmail.value, authPassword.value)
    }
    localStorage.setItem('coomate-token', resp.token)
    localStorage.setItem('coomate-user', JSON.stringify(resp.user))
    store.setAuth(resp.token, resp.user)
    closeAuthModal()
    showToast(authMode.value === 'register' ? '注册成功' : '登录成功')
    await store.loadConversationList()
  } catch (e: any) {
    authError.value = e.message || '操作失败'
  } finally {
    authLoading.value = false
  }
}

async function handleGuest() {
  try {
    const resp = await api.guestLogin()
    localStorage.setItem('coomate-token', resp.token)
    localStorage.setItem('coomate-user', JSON.stringify(resp.user))
    store.setAuth(resp.token, resp.user)
    closeAuthModal()
    showToast('已进入游客模式')
    await store.loadConversationList()
  } catch {
    showToast('游客模式启动失败')
  }
}

function handleLogout() {
  api.logout().catch(() => {})
  localStorage.removeItem('coomate-token')
  localStorage.removeItem('coomate-user')
  store.clearAuth()
  showToast('已退出登录')
}

// --- Toast ---
const toastMessage = ref('')
const toastVisible = ref(false)
let toastTimer: ReturnType<typeof setTimeout>

function showToast(msg: string, duration = 2000) {
  toastMessage.value = msg
  toastVisible.value = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastVisible.value = false }, duration)
}

// --- Init ---
onMounted(() => {
  const savedUser = localStorage.getItem('coomate-user')
  const savedToken = localStorage.getItem('coomate-token')
  if (savedUser && savedToken) {
    try {
      const user = JSON.parse(savedUser)
      store.setAuth(savedToken, user)
    } catch {}
  }

  store.loadConversationList()
})
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-main text-text-primary">
    <!-- Sidebar Left with animation -->
    <Transition name="sidebar-left">
      <LeftSidebar
        v-if="uiStore.leftSidebarOpen"
        :currentUser="store.currentUser"
        @openAuthModal="openAuthModal"
        @logout="handleLogout"
      />
    </Transition>

    <!-- Main -->
    <main class="flex-1 min-w-0 flex flex-col relative w-full h-full">
      <!-- Header -->
      <header
        class="flex-shrink-0 flex items-center justify-between px-4 py-3 bg-main relative z-10"
      >
        <div class="flex items-center gap-3">
          <button
            class="flex-shrink-0 w-9 h-9 flex items-center justify-center rounded-lg text-text-secondary hover:bg-card-hover transition-colors"
            @click="uiStore.toggleLeftSidebar"
            title="切换左侧边栏"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span class="text-lg font-semibold text-text-primary">
            CooMate
          </span>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="flex-shrink-0 w-9 h-9 flex items-center justify-center rounded-lg text-text-secondary hover:bg-card-hover transition-colors"
            @click="uiStore.toggleRightSidebar"
            title="思考节点"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </button>
        </div>
      </header>

      <!-- Chat Area (includes input) -->
      <ChatPanel class="flex-1" />
    </main>

    <!-- Sidebar Right with animation -->
    <Transition name="sidebar-right">
      <RightSidebar v-if="uiStore.rightSidebarOpen" />
    </Transition>
  </div>

  <!-- Auth Modal -->
  <div class="modal-overlay" :class="{ show: showAuthModal }" @click.self="closeAuthModal">
    <div class="modal-content">
      <div class="flex items-center justify-between mb-5">
        <div class="text-lg font-semibold" style="color: var(--text-primary)">{{ authMode === 'login' ? '登录' : '注册' }}</div>
        <button class="p-1 rounded transition-colors" style="color: var(--text-secondary)" @click="closeAuthModal">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div v-if="authError" class="mb-3 text-sm px-3 py-2 rounded-lg" style="background: rgba(239,68,68,0.1); color: #ef4444">
        {{ authError }}
      </div>
      <div class="flex flex-col gap-3">
        <input
          v-if="authMode === 'register'"
          v-model="authName"
          type="text"
          placeholder="昵称（可选）"
          class="login-input"
        />
        <input
          v-model="authEmail"
          type="email"
          placeholder="邮箱地址"
          class="login-input"
        />
        <input
          v-model="authPassword"
          type="password"
          placeholder="密码"
          class="login-input"
          @keydown.enter="handleAuth"
        />
        <button
          class="w-full py-2.5 rounded-lg text-sm font-medium text-white transition-colors"
          style="background: var(--accent)"
          :disabled="authLoading || !authEmail || !authPassword"
          :style="{ opacity: authLoading || !authEmail || !authPassword ? '0.5' : '1' }"
          @click="handleAuth"
        >
          {{ authLoading ? '处理中...' : (authMode === 'login' ? '登录' : '注册') }}
        </button>
        <div class="flex items-center gap-3 text-xs" style="color: var(--text-muted)">
          <div class="flex-1 h-px" style="background: var(--border)"></div>
          <span>或</span>
          <div class="flex-1 h-px" style="background: var(--border)"></div>
        </div>
        <button
          class="w-full py-2.5 rounded-lg text-sm font-medium border transition-colors"
          :style="{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }"
          @click="handleGuest"
        >
          游客模式继续
        </button>
      </div>
    </div>
  </div>

  <!-- Toast -->
  <div class="toast" :class="{ show: toastVisible }">{{ toastMessage }}</div>
</template>

<style scoped>
.login-input {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  transition: border-color var(--transition);
}
.login-input::placeholder {
  color: var(--text-muted);
}
.login-input:focus {
  border-color: var(--accent);
}

/* Sidebar animations */
.sidebar-left-enter-active,
.sidebar-left-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-left-enter-from {
  transform: translateX(-100%);
  opacity: 0;
}

.sidebar-left-leave-to {
  transform: translateX(-100%);
  opacity: 0;
}

.sidebar-right-enter-active,
.sidebar-right-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-right-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.sidebar-right-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
</style>
