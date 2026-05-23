<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AuthDialog from "../components/auth/AuthDialog.vue";
import CommandLineIcon from "../components/icons/CommandLineIcon.vue";
import { useChatStore } from "../stores/chat";

const route = useRoute();
const router = useRouter();
const chatStore = useChatStore();
const authMode = ref<"login" | "register">("login");

const isAuthenticated = computed(() => Boolean(chatStore.authToken));

const isDialogVisible = computed(() => route.query.auth === "login" || route.query.auth === "register");

watch(
  () => route.query.auth,
  (value) => {
    authMode.value = value === "register" ? "register" : "login";
  },
  { immediate: true }
);

function openLogin() {
  if (isAuthenticated.value) {
    void router.push({ name: "chat" });
    return;
  }

  authMode.value = "login";
  void router.replace({
    name: "landing",
    query: { ...route.query, auth: "login" }
  });
}

function openRegister() {
  if (isAuthenticated.value) {
    void router.push({ name: "chat" });
    return;
  }

  authMode.value = "register";
  void router.replace({
    name: "landing",
    query: { ...route.query, auth: "register" }
  });
}

function closeAuthDialog() {
  const query = { ...route.query };
  delete query.auth;
  void router.replace({
    name: "landing",
    query
  });
}

function switchAuthMode(mode: "login" | "register") {
  authMode.value = mode;
  void router.replace({
    name: "landing",
    query: { ...route.query, auth: mode }
  });
}

function handleAuthSuccess() {
  closeAuthDialog();
  void router.push({ name: "chat" });
}
</script>

<template>
  <main class="landing-shell">
    <div class="landing-glow landing-glow-left" aria-hidden="true"></div>
    <div class="landing-glow landing-glow-right" aria-hidden="true"></div>
    <div class="landing-watermark" aria-hidden="true">
      <CommandLineIcon :size="220" :stroke-width="1.2" framed />
    </div>

    <section class="landing-panel">
      <div class="landing-kicker">
        <CommandLineIcon :size="20" :stroke-width="1.7" animated />
        <span>CooMate Workspace</span>
      </div>

      <h1 class="landing-title">CooMate</h1>
      <p class="landing-subtitle">想清楚，再出发</p>

      <div class="landing-copy">
        <p>从目标澄清到思路收敛，每一步都用更轻、更安静、更专业的方式呈现。</p>
        <p>你只需要说出困惑，系统会引导你自己找到答案。</p>
      </div>

      <div class="landing-actions">
        <div class="landing-action-row">
          <button class="landing-button landing-button-primary" type="button" @click="openLogin">
            {{ isAuthenticated ? "进入工作台" : "登录" }}
          </button>
          <button
            v-if="!isAuthenticated"
            class="landing-button landing-button-secondary"
            type="button"
            @click="openRegister"
          >
            注册
          </button>
          <div v-else class="landing-signed-in">
            <span class="landing-signed-in-label">当前账号</span>
            <span class="landing-signed-in-name">{{ chatStore.currentUser?.name }}</span>
          </div>
        </div>
      </div>
    </section>

    <AuthDialog
      v-if="isDialogVisible"
      :mode="authMode"
      @close="closeAuthDialog"
      @success="handleAuthSuccess"
      @switch-mode="switchAuthMode"
    />
  </main>
</template>

<style scoped>
.landing-shell {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 48px 24px;
  color: var(--text-primary);
}

.landing-shell::before {
  content: "";
  position: absolute;
  inset: 24px;
  border: 1px solid var(--line-soft);
  pointer-events: none;
}

.landing-glow {
  position: absolute;
  width: 38vw;
  height: 38vw;
  border-radius: 999px;
  filter: blur(50px);
  opacity: 0.16;
  pointer-events: none;
}

.landing-glow-left {
  left: -8vw;
  top: -12vh;
  background: var(--accent-blue);
}

.landing-glow-right {
  right: -6vw;
  bottom: -12vh;
  background: var(--accent-amber);
}

.landing-watermark {
  position: absolute;
  right: 7vw;
  bottom: 8vh;
  color: rgba(62, 111, 230, 0.08);
  pointer-events: none;
}

.landing-panel {
  position: relative;
  z-index: 1;
  width: min(760px, 100%);
  padding: 28px 0;
}

.landing-kicker {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--line-default);
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.landing-kicker :deep(svg) {
  color: var(--accent-blue);
}

.landing-title {
  margin: 26px 0 0;
  font-size: clamp(48px, 8vw, 88px);
  line-height: 1;
  letter-spacing: 0.01em;
  font-weight: 500;
  font-style: italic;
  font-family:
    "Snell Roundhand",
    "Segoe Script",
    "Brush Script MT",
    "Lucida Handwriting",
    "Apple Chancery",
    cursive;
  color: var(--text-primary);
}

.landing-subtitle {
  margin: 20px 0 0;
  max-width: 620px;
  font-size: clamp(18px, 2vw, 24px);
  line-height: 1.45;
  color: var(--text-secondary);
}

.landing-copy {
  display: grid;
  gap: 14px;
  margin-top: 36px;
  padding-top: 24px;
  border-top: 1px solid var(--line-soft);
  max-width: 620px;
}

.landing-copy p {
  margin: 0;
  font-size: 14px;
  line-height: 1.9;
  color: var(--text-secondary);
}

.landing-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-top: 44px;
}

.landing-action-row {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.landing-signed-in {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 11px 16px;
  border: 1px solid var(--line-default);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.52);
  color: var(--text-secondary);
}

.landing-signed-in-label {
  font-size: 11px;
  font-family: var(--font-mono);
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
}

.landing-signed-in-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.landing-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 132px;
  padding: 14px 30px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.04em;
  transition:
    transform 0.18s ease,
    filter 0.18s ease,
    border-color 0.18s ease,
    background-color 0.18s ease,
    color 0.18s ease;
}

.landing-button:hover {
  transform: translateY(-1px);
  filter: brightness(1.03);
}

.landing-button-primary {
  border: none;
  background: linear-gradient(135deg, var(--text-primary), #243149);
  color: var(--text-inverse);
  box-shadow: var(--shadow-soft);
}

.landing-button-secondary {
  border: 1px solid var(--line-default);
  background: rgba(255, 255, 255, 0.54);
  color: var(--text-primary);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.36);
}

@media (max-width: 760px) {
  .landing-shell {
    padding: 28px 18px;
  }

  .landing-shell::before {
    inset: 14px;
  }

  .landing-watermark {
    right: 2vw;
    bottom: 5vh;
    transform: scale(0.72);
    transform-origin: bottom right;
  }

  .landing-action-row {
    width: 100%;
  }

  .landing-button {
    flex: 1 1 180px;
  }
}
</style>
