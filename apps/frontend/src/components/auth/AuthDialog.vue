<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import * as api from "../../services/api";

const props = defineProps<{
  mode: "login" | "register";
}>();

const emit = defineEmits<{
  close: [];
  success: [];
  "switch-mode": [mode: "login" | "register"];
}>();

const errorMessage = ref("");
const isSubmitting = ref(false);

const loginForm = reactive({
  username: "",
  password: ""
});

const registerForm = reactive({
  username: "",
  password: ""
});

const isLoginMode = computed(() => props.mode === "login");
const title = computed(() => (isLoginMode.value ? "登录账号" : "创建账号"));
const actionLabel = computed(() => (isLoginMode.value ? "立即登录" : "创建并进入"));
const switchLabel = computed(() => (isLoginMode.value ? "还没有账号？去注册" : "已经有账号？去登录"));

watch(
  () => props.mode,
  () => {
    errorMessage.value = "";
  }
);

function closeDialog() {
  emit("close");
}

function switchMode() {
  emit("switch-mode", isLoginMode.value ? "register" : "login");
}

async function submit() {
  errorMessage.value = "";
  isSubmitting.value = true;

  try {
    let resp: api.AuthResponse;
    if (isLoginMode.value) {
      resp = await api.login(loginForm.username, loginForm.password);
    } else {
      resp = await api.register(registerForm.username, registerForm.password);
    }
    localStorage.setItem("coomate-token", resp.token);
    localStorage.setItem("coomate-user", JSON.stringify(resp.user));
    emit("success");
  } catch (error) {
    if (error instanceof Error && error.message) {
      const raw = error.message.replace(/^HTTP \d+:\s*/, "").trim();
      errorMessage.value = raw || "提交失败，请稍后重试。";
    } else {
      errorMessage.value = "提交失败，请稍后重试。";
    }
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <div class="auth-overlay" @click.self="closeDialog">
    <section class="auth-dialog" role="dialog" aria-modal="true" :aria-label="title">
      <button class="auth-close" type="button" aria-label="关闭" @click="closeDialog">
        <span></span>
        <span></span>
      </button>

      <div class="auth-kicker">{{ isLoginMode ? "ACCOUNT ACCESS" : "ACCOUNT SETUP" }}</div>
      <h2 class="auth-title">{{ title }}</h2>

      <form class="auth-form" @submit.prevent="submit">
        <template v-if="isLoginMode">
          <label class="auth-field">
            <span>用户名</span>
            <input v-model.trim="loginForm.username" type="text" autocomplete="username" />
          </label>

          <label class="auth-field">
            <span>密码</span>
            <input
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              autocomplete="current-password"
            />
          </label>
        </template>

        <template v-else>
          <label class="auth-field">
            <span>用户名</span>
            <input v-model.trim="registerForm.username" type="text" autocomplete="username" />
          </label>

          <label class="auth-field">
            <span>密码</span>
            <input
              v-model="registerForm.password"
              type="password"
              placeholder="至少 8 位"
              autocomplete="new-password"
            />
          </label>


        </template>

        <p v-if="errorMessage" class="auth-error">{{ errorMessage }}</p>

        <div class="auth-actions">
          <button class="auth-submit" type="submit" :disabled="isSubmitting">
            {{ isSubmitting ? "处理中..." : actionLabel }}
          </button>

          <button class="auth-switch" type="button" @click="switchMode">
            {{ switchLabel }}
          </button>
        </div>
      </form>
    </section>
  </div>
</template>

<style scoped>
.auth-overlay {
  position: fixed;
  inset: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px;
  background: rgba(246, 245, 241, 0.36);
  backdrop-filter: blur(10px);
}

.auth-dialog {
  position: relative;
  width: min(520px, 100%);
  padding: 34px 32px 30px;
  background: rgba(251, 250, 247, 0.88);
  border: 1px solid var(--line-default);
  border-radius: 32px;
  box-shadow: var(--shadow-float);
}

.auth-dialog::before {
  content: "";
  position: absolute;
  inset: 16px;
  border: 1px solid var(--line-soft);
  border-radius: 22px;
  pointer-events: none;
}

.auth-close {
  position: absolute;
  top: 18px;
  right: 18px;
  width: 36px;
  height: 36px;
  border: 1px solid var(--line-soft);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
}

.auth-close span {
  position: absolute;
  top: 17px;
  left: 10px;
  width: 14px;
  height: 1.5px;
  background: var(--text-secondary);
}

.auth-close span:first-child {
  transform: rotate(45deg);
}

.auth-close span:last-child {
  transform: rotate(-45deg);
}

.auth-kicker {
  display: inline-flex;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line-default);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.12em;
  color: var(--text-tertiary);
}

.auth-title {
  margin: 22px 0 10px;
  font-size: clamp(32px, 5vw, 42px);
  line-height: 0.98;
  letter-spacing: -0.04em;
}

.auth-form {
  display: grid;
  gap: 16px;
  margin-top: 28px;
}

.auth-field {
  display: grid;
  gap: 8px;
}

.auth-field span {
  font-size: 12px;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
}

.auth-field input {
  width: 100%;
  padding: 14px 0 12px;
  border: none;
  border-bottom: 1px solid var(--line-default);
  background: transparent;
  font-size: 14px;
  transition: border-color 0.18s ease;
}

.auth-field input:focus {
  outline: none;
  border-bottom-color: var(--accent-blue);
}

.auth-error {
  margin: 0;
  padding: 10px 14px;
  border-radius: 16px;
  background: var(--accent-danger-soft);
  color: var(--accent-danger);
  font-size: 12px;
  line-height: 1.6;
}

.auth-actions {
  display: grid;
  gap: 12px;
  margin-top: 6px;
}

.auth-submit,
.auth-switch {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  min-height: 50px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.auth-submit {
  border: none;
  background: linear-gradient(135deg, var(--text-primary), #243149);
  color: var(--text-inverse);
  box-shadow: var(--shadow-soft);
}

.auth-submit:disabled {
  opacity: 0.58;
  cursor: not-allowed;
}

.auth-switch {
  border: 1px solid var(--line-default);
  background: rgba(255, 255, 255, 0.5);
  color: var(--text-primary);
}

@media (max-width: 640px) {
  .auth-overlay {
    padding: 18px;
  }

  .auth-dialog {
    padding: 28px 22px 24px;
    border-radius: 24px;
  }

  .auth-dialog::before {
    inset: 10px;
    border-radius: 18px;
  }
}
</style>
