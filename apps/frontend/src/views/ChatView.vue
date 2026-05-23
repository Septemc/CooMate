<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useChatStore } from "../stores/chat";
import { useUIStore } from "../stores/ui";
import * as api from "../services/api";
import CommandLineIcon from "../components/icons/CommandLineIcon.vue";
import { marked } from "marked";

const route = useRoute();
const router = useRouter();
const chatStore = useChatStore();
const uiStore = useUIStore();

const initInput = ref("");
const activeInput = ref("");
const initFocused = ref(false);
const activeFocused = ref(false);
const toastVisible = ref(false);
const toastTitle = ref("");
const toastDesc = ref("");
const msgScrollRef = ref<HTMLElement | null>(null);
const sidebarSearchInput = ref("");
const sidebarOpenSection = ref<"history">("history")
const stepOtherInputs = ref<Record<string, string>>({})
const supplementInputs = ref<Record<string, string>>({})

let toastTimer: number | null = null;

const hasConversation = computed(() => chatStore.messages.length > 0);
const displayConversations = computed(() => {
  const keyword = sidebarSearchInput.value.trim().toLowerCase();
  if (!keyword) {
    return chatStore.conversations;
  }
  return chatStore.conversations.filter((conv) =>
    conv.title.toLowerCase().includes(keyword)
  );
});
const activeSessionTitle = computed(() => chatStore.currentTitle);
const currentUserLabel = computed(() => chatStore.currentUser?.name ?? "用户");
const sidebarCollapsed = computed(() => !uiStore.leftSidebarOpen);

const canInitSend = computed(() => initInput.value.trim().length > 0 && !chatStore.isLoading);
const canActiveSend = computed(
  () => activeInput.value.trim().length > 0 && !chatStore.isLoading
);

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatBubbleContent(text: string) {
  const escaped = escapeHtml(text).replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  return escaped
    .split("\n")
    .map((line) => (line.trim() ? `<p>${line}</p>` : "<br>"))
    .join("");
}

function showToast(title: string, desc: string) {
  toastTitle.value = title;
  toastDesc.value = desc;
  toastVisible.value = true;

  if (toastTimer) {
    window.clearTimeout(toastTimer);
  }

  toastTimer = window.setTimeout(() => {
    toastVisible.value = false;
  }, 2600);
}

function scrollBottom() {
  nextTick(() => {
    if (!msgScrollRef.value) {
      return;
    }
    msgScrollRef.value.scrollTop = msgScrollRef.value.scrollHeight;
  });
}

function collapseSidebar() {
  uiStore.leftSidebarOpen = false;
}

function expandSidebar() {
  uiStore.leftSidebarOpen = true;
}

function setSidebarSection(section: "history") {
  sidebarOpenSection.value = section;
}

function getSessionInitial(title: string) {
  return title.trim().slice(0, 1) || "会";
}

async function handleInitSend() {
  const value = initInput.value.trim();
  if (!value) {
    return;
  }

  initInput.value = "";

  try {
    await chatStore.sendMessage(value);
    scrollBottom();
  } catch {
    showToast("发送失败", "请检查接口服务状态后重试。");
  }
}

async function handleActiveSend() {
  const value = activeInput.value.trim();
  if (!value) {
    return;
  }

  activeInput.value = "";

  try {
    await chatStore.sendMessage(value);
    scrollBottom();
  } catch (error) {
    const detail =
      error instanceof Error && error.message
        ? error.message
        : "当前消息未成功提交，请稍后重试。";
    console.error("[chat stream failed]", error);
    showToast("发送失败", detail);
  }
}

async function handleHistoryClick(conversationId: string) {
  try {
    await chatStore.loadConversation(conversationId);
    scrollBottom();
  } catch {
    showToast("读取失败", "历史会话加载失败，请稍后重试。");
  }
}

async function handleDeleteConversation(conversationId: string, event: Event) {
  event.stopPropagation();
  try {
    await chatStore.removeConversation(conversationId);
  } catch {
    showToast("删除失败", "请稍后重试。");
  }
}

function handleNewConversation() {
  chatStore.startNewConversation()
  initInput.value = ""
  activeInput.value = ""
  stepOtherInputs.value = {}
  supplementInputs.value = {}
}

const stepRewriteInputs = ref<Record<string, string>>({})

marked.setOptions({
  breaks: true,
  gfm: true,
})

function renderMarkdown(text: string): string {
  return marked.parse(text) as string
}

function startRewrite(msgId: string, stepNum: number) {
  const key = msgId + "-" + stepNum
  const existing = chatStore.messages.find(m => m.id === msgId)?.stepAnswers?.find(a => a.step === stepNum)?.answer || ""
  stepRewriteInputs.value[key] = existing
}

function cancelRewrite(msgId: string, stepNum: number) {
  const key = msgId + "-" + stepNum
  delete stepRewriteInputs.value[key]
}

function confirmRewrite(msgId: string, stepNum: number) {
  const key = msgId + "-" + stepNum
  const val = stepRewriteInputs.value[key]?.trim()
  if (val) {
    chatStore.answerStep(msgId, stepNum, val)
  }
  delete stepRewriteInputs.value[key]
}

function isRewriting(msgId: string, stepNum: number) {
  return stepRewriteInputs.value[msgId + "-" + stepNum] !== undefined
}

function submitStepOther(msgId: string, stepNum: number) {
  const key = msgId + "-" + stepNum
  const val = stepOtherInputs.value[key]?.trim()
  if (val) {
    chatStore.answerStep(msgId, stepNum, val)
    stepOtherInputs.value[key] = ""
  }
}

function submitSupplement(msgId: string) {
  const val = supplementInputs.value[msgId]?.trim()
  chatStore.completeSupplement(msgId, val || "")
  supplementInputs.value[msgId] = ""
}

async function handleLogout() {
  api.logout().catch(() => {});
  localStorage.removeItem("coomate-token");
  localStorage.removeItem("coomate-user");
  chatStore.clearAuth();
  showToast("已退出", "已退出登录。");
  await router.push({ name: "landing", query: { auth: "login" } });
}

onMounted(async () => {
  await chatStore.loadConversationList();
  const queryValue = route.query.q;
  if (typeof queryValue === "string" && queryValue.trim()) {
    initInput.value = queryValue.trim();
    await handleInitSend();
  }
});

watch(
  () => [
    chatStore.messages.length,
    chatStore.streamingContent,
    chatStore.isLoading
  ],
  () => {
    scrollBottom();
  }
);
</script>

<template>
  <div class="locked-chat-page">
    <div class="watermark" aria-hidden="true">
      <CommandLineIcon :size="240" :stroke-width="1.15" framed />
    </div>

    <div id="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sb-full">
        <div class="sb-header">
          <div class="sb-user-row">
            <div class="robot-avatar" aria-hidden="true">
              <CommandLineIcon :size="18" :stroke-width="1.8" animated />
            </div>
            <span>CooMate</span>
          </div>
          <button class="icon-btn" type="button" @click="collapseSidebar" aria-label="收起侧边栏">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
              <path
                d="M15 18L9 12L15 6"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </button>
        </div>

        <div class="sb-new-wrap">
          <button class="sb-new-btn" type="button" @click="handleNewConversation">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 5V19M5 12H19"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <span>开始新对话</span>
          </button>
        </div>

        <div class="sb-search-wrap">
          <div class="sb-search-box">
            <svg class="sb-search-icon" width="13" height="13" viewBox="0 0 24 24" fill="none">
              <circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2" />
              <path
                d="M20 20L16.5 16.5"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
              />
            </svg>
            <input
              v-model="sidebarSearchInput"
              @focus="setSidebarSection('history')"
              class="sb-search-input"
              type="text"
              placeholder="搜索历史对话..."
            />
            <button
              v-if="sidebarSearchInput"
              class="sb-search-clear"
              type="button"
              aria-label="清除搜索"
              @click="sidebarSearchInput = ''"
            >
              ×
            </button>
          </div>
        </div>

        <section class="sb-sidebar-section sb-history">
          <button
            class="sb-section-toggle"
            type="button"
            :class="{ open: sidebarOpenSection === 'history' }"
            @click="setSidebarSection('history')"
          >
            <span class="sb-section-title">历史记录</span>
            <svg class="sb-section-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path
                d="M6 9L12 15L18 9"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </button>
          <div v-if="sidebarOpenSection === 'history'" class="sb-section-body">
            <template v-if="displayConversations.length">
              <div
                v-for="conv in displayConversations"
                :key="conv.id"
                class="sb-item-wrapper"
              >
                <button
                  class="sb-item"
                  :class="{ active: chatStore.currentConversationId === conv.id }"
                  type="button"
                  @click="handleHistoryClick(conv.id)"
                >
                  {{ conv.title }}
                </button>
                <button
                  class="sb-item-delete"
                  type="button"
                  title="删除"
                  @click="handleDeleteConversation(conv.id, $event)"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                    <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                </button>
              </div>
            </template>
            <div v-else class="sb-empty">
              {{ sidebarSearchInput ? "没有匹配的历史会话" : "暂无历史会话" }}
            </div>
          </div>
        </section>
      </div>

      <div class="sb-mini">
        <button class="sb-mini-expand" type="button" @click="expandSidebar" aria-label="展开侧边栏">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <path
              d="M9 18L15 12L9 6"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
        <div class="sb-mini-divider"></div>
        <button
          v-for="conv in displayConversations.slice(0, 4)"
          :key="conv.id"
          class="sb-mini-dot"
          type="button"
          :title="conv.title"
          @click="handleHistoryClick(conv.id)"
        >
          {{ getSessionInitial(conv.title) }}
        </button>
      </div>
    </div>

    <div id="main">
      <header id="topbar">
        <div class="topbar-left">
          <div class="exp-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path
                d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <path
                d="M14 3v6h6"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <span>{{ activeSessionTitle }}</span>
          </div>
        </div>

        <div class="topbar-right">
          <div class="topbar-user">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <path
                d="M20 21V19A4 4 0 0 0 16 15H8A4 4 0 0 0 4 19V21"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2" />
            </svg>
            <span>{{ currentUserLabel }}</span>
            <button class="topbar-logout-btn" type="button" @click="handleLogout" title="退出登录">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <polyline points="16 17 21 12 16 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <line x1="21" y1="12" x2="9" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </header>

      <transition name="state-swap" mode="out-in">
        <div v-if="!hasConversation" id="initialState" key="initial">
          <div class="init-hero">
            <h1>CooMate</h1>
            <div class="init-subtitle">想清楚，再出发</div>
            <div class="init-desc">
              我不会直接给你答案。<br />
              我会通过结构化提问，引导你自己找到答案。
            </div>
          </div>

          <div class="init-card-wrap">
            <div class="init-input-shell" :class="{ focused: initFocused }">
              <div class="init-glow-orb init-glow-blue" aria-hidden="true"></div>
              <div class="init-glow-orb init-glow-amber" aria-hidden="true"></div>
              <div class="init-input-label">
                <CommandLineIcon :size="15" :stroke-width="1.7" />
                <span>说出你的困惑</span>
              </div>
              <textarea
                v-model="initInput"
                placeholder="例如：我纠结要不要分手"
                rows="5"
                @keydown.enter.exact.prevent="handleInitSend"
                @focus="initFocused = true"
                @blur="initFocused = false"
              />
              <button class="send-circle" type="button" :disabled="!canInitSend" @click="handleInitSend">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M12 19V5M5 12l7-7 7 7" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </button>
              <Transition name="ring-fade">
                <span v-if="initFocused" class="focus-ring"></span>
              </Transition>
            </div>
          </div>
        </div>

        <div v-else id="activeState" key="active">
          <div id="msgScroll" ref="msgScrollRef">
            <div id="msgList">
              <template v-for="(msg, idx) in chatStore.messages" :key="msg.id">
                <div
                  class="msg-row"
                  :class="{ 'user-row': msg.role === 'user' }"
                >
                  <template v-if="msg.role === 'user'">
                    <div class="bubble-user">{{ msg.content }}</div>
                    <div class="avatar avatar-user" aria-hidden="true">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                        <path
                          d="M20 21V19A4 4 0 0 0 16 15H8A4 4 0 0 0 4 19V21"
                          stroke="currentColor"
                          stroke-width="2"
                          stroke-linecap="round"
                          stroke-linejoin="round"
                        />
                        <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2" />
                      </svg>
                    </div>
                  </template>

                  <template v-else>
                    <div class="avatar avatar-ai" aria-hidden="true">
                      <CommandLineIcon :size="18" :stroke-width="1.7" animated />
                    </div>
                    <div class="bubble-ai-wrap">
                      <template v-if="msg.steps && msg.steps.length > 0 && msg.steps[0].step > 0 && !(idx === chatStore.messages.length - 1 && chatStore.isLoading)">
                        <template v-for="step in msg.steps" :key="step.step">
                          <div
                            v-if="msg.currentStep != null && step.step <= msg.currentStep"
                            class="bubble-ai"
                          >
                            <div class="step-header">
                              <span class="step-badge">0{{ step.step }}</span>
                              <span class="step-title">{{ step.title }}</span>
                            </div>
                            <div
                              class="step-body"
                              v-html="formatBubbleContent(step.content)"
                            />
                            <div
                              v-if="step.step === msg.currentStep && !msg.isStepComplete && !msg.stepAnswers?.some(a => a.step === step.step)"
                              class="step-interact"
                            >
                              <div class="step-options">
                                <template v-if="step.options && step.options.length > 0">
                                  <button
                                    v-for="opt in step.options"
                                    :key="opt.key"
                                    class="step-opt-btn"
                                    type="button"
                                    @click="chatStore.answerStep(msg.id, step.step, opt.label)"
                                  >
                                    <span class="step-opt-key">{{ opt.key }}</span>
                                    <span class="step-opt-label">{{ opt.label }}</span>
                                  </button>
                                </template>
                                <div v-else class="step-options-loading">
                                  <div class="dots">
                                    <div class="dot"></div>
                                    <div class="dot"></div>
                                    <div class="dot"></div>
                                  </div>
                                  <span>正在生成选项...</span>
                                </div>
                              </div>
                              <div class="step-other-row">
                                <input
                                  v-model="stepOtherInputs[msg.id + '-' + step.step]"
                                  class="step-other-input"
                                  type="text"
                                  placeholder="或者输入你的想法..."
                                  @keydown.enter.exact.prevent="submitStepOther(msg.id, step.step)"
                                />
                                <button
                                  class="step-other-submit"
                                  type="button"
                                  :disabled="!stepOtherInputs[msg.id + '-' + step.step]?.trim()"
                                  @click="submitStepOther(msg.id, step.step)"
                                >
                                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                                    <path d="M12 19V5M5 12l7-7 7 7" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                                  </svg>
                                </button>
                              </div>
                              <button class="step-skip-btn" type="button" @click="chatStore.skipStep(msg.id, step.step)">
                                跳过此步
                              </button>
                            </div>
                            <div
                              v-if="msg.stepAnswers?.some(a => a.step === step.step)"
                              class="step-answer"
                            >
                              <template v-if="isRewriting(msg.id, step.step)">
                                <div class="step-rewrite-row">
                                  <input
                                    v-model="stepRewriteInputs[msg.id + '-' + step.step]"
                                    class="step-other-input"
                                    type="text"
                                    placeholder="输入新的回答..."
                                    @keydown.enter.exact.prevent="confirmRewrite(msg.id, step.step)"
                                  />
                                  <button class="step-rewrite-confirm" type="button" @click="confirmRewrite(msg.id, step.step)">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                                      <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                                    </svg>
                                  </button>
                                  <button class="step-rewrite-cancel" type="button" @click="cancelRewrite(msg.id, step.step)">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                                      <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                                    </svg>
                                  </button>
                                </div>
                              </template>
                              <template v-else>
                                <span class="step-answer-label">你的回答</span>
                                <span
                                  v-if="msg.stepAnswers.find(a => a.step === step.step)?.answer"
                                  class="step-answer-text"
                                >{{ msg.stepAnswers.find(a => a.step === step.step)?.answer }}</span>
                                <span v-else class="step-answer-text step-answer-skipped">已跳过</span>
                                <button class="step-rewrite-btn" type="button" @click="startRewrite(msg.id, step.step)">重写</button>
                              </template>
                            </div>
                          </div>
                        </template>

                        <div
                          v-if="msg.currentStep != null && msg.currentStep > msg.steps.filter(s => s.step > 0).length && !msg.isStepComplete"
                          class="bubble-ai step-supplement"
                        >
                          <div class="step-header">
                            <span class="step-badge step-badge-final">✦</span>
                            <span class="step-title">您还有什么要补充的吗？</span>
                          </div>
                          <div class="step-interact">
                            <div class="step-other-row">
                              <input
                                v-model="supplementInputs[msg.id]"
                                class="step-other-input"
                                type="text"
                                placeholder="输入补充内容，或直接完成..."
                                @keydown.enter.exact.prevent="submitSupplement(msg.id)"
                              />
                              <button
                                class="step-other-submit"
                                type="button"
                                @click="submitSupplement(msg.id)"
                              >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                                  <path d="M12 19V5M5 12l7-7 7 7" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                              </button>
                            </div>
                            <button class="step-skip-btn" type="button" @click="chatStore.completeSupplement(msg.id, '')">
                              完成，无需补充
                            </button>
                          </div>
                        </div>
                      </template>

                      <template v-else-if="idx === chatStore.messages.length - 1 && chatStore.isLoading">
                        <div class="typing-bubble">
                          <div class="dots">
                            <div class="dot"></div>
                            <div class="dot"></div>
                            <div class="dot"></div>
                          </div>
                        </div>
                      </template>

                      <template v-else>
                        <div
                          v-if="msg.content.trim()"
                          class="bubble-ai"
                          :class="{ 'bubble-markdown': msg.isSummary }"
                          v-html="msg.isSummary ? renderMarkdown(msg.content) : formatBubbleContent(msg.content)"
                        />
                      </template>
                    </div>
                  </template>
                </div>
              </template>
            </div>
          </div>

          <div id="bottomBar">
            <div class="bottom-inner">
              <div class="bottom-card" :class="{ focused: activeFocused }">
                <div class="bottom-glow-orb bottom-glow-blue" aria-hidden="true"></div>
                <textarea
                  v-model="activeInput"
                  placeholder="输入指令..."
                  rows="2"
                  @keydown.enter.exact.prevent="handleActiveSend"
                  @focus="activeFocused = true"
                  @blur="activeFocused = false"
                />
                <button
                  class="send-circle"
                  type="button"
                  :disabled="!canActiveSend"
                  @click="handleActiveSend"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M12 19V5M5 12l7-7 7 7" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </button>
                <Transition name="ring-fade">
                  <span v-if="activeFocused" class="focus-ring-bottom"></span>
                </Transition>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <div id="toast" :class="{ show: toastVisible }">
      <div id="toast-title">{{ toastTitle }}</div>
      <div id="toast-desc">{{ toastDesc }}</div>
    </div>
  </div>
</template>

<style scoped>
*,
*::before,
*::after {
  box-sizing: border-box;
}

.locked-chat-page {
  font-family:
    "SF Pro Display", "PingFang SC", "Noto Sans SC", "Segoe UI", "Microsoft YaHei",
    sans-serif;
  height: 100vh;
  width: 100%;
  display: flex;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(62, 111, 230, 0.07), transparent 24%),
    radial-gradient(circle at right 78%, rgba(183, 121, 31, 0.07), transparent 22%),
    linear-gradient(180deg, rgba(251, 250, 247, 0.96), rgba(246, 245, 241, 0.98));
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  position: relative;
}

.locked-chat-page::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.36), transparent 18%);
  pointer-events: none;
  z-index: 0;
}

.locked-chat-page::after {
  content: "";
  position: absolute;
  inset: 18px;
  border: 1px solid var(--line-soft);
  pointer-events: none;
  z-index: 0;
}

.watermark {
  position: fixed;
  bottom: 3vh;
  right: 3vw;
  width: 340px;
  height: 340px;
  opacity: 0.1;
  color: rgba(62, 111, 230, 0.1);
  transform: rotate(-3deg);
  pointer-events: none;
  z-index: 0;
}

#sidebar {
  width: 240px;
  min-width: 240px;
  height: 100vh;
  background: rgba(248, 246, 241, 0.76);
  border-right: 1px solid var(--line-default);
  backdrop-filter: blur(24px);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  z-index: 20;
  transition:
    width 0.22s ease,
    min-width 0.22s ease;
  overflow: hidden;
}

#sidebar.collapsed {
  width: 56px;
  min-width: 56px;
}

.sb-full {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

#sidebar.collapsed .sb-full {
  display: none;
}

.sb-mini {
  display: none;
  flex-direction: column;
  align-items: center;
  padding: 14px 0;
  gap: 10px;
  height: 100%;
}

#sidebar.collapsed .sb-mini {
  display: flex;
}

.sb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 18px 16px;
  border-bottom: 1px solid var(--line-soft);
}

.sb-user-row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  font-weight: 650;
  letter-spacing: -0.01em;
  color: var(--text-primary);
}

.sb-user-row > span {
  font-family:
    "Snell Roundhand",
    "Segoe Script",
    "Brush Script MT",
    "Lucida Handwriting",
    "Apple Chancery",
    cursive;
  font-size: 16px;
  font-weight: 500;
  font-style: italic;
  letter-spacing: 0.01em;
  line-height: 1;
  color: var(--text-primary);
}

.robot-avatar,
.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.robot-avatar,
.avatar-ai {
  width: auto;
  height: auto;
  border-radius: 0;
  background: none;
  border: none;
  color: var(--accent-blue);
}

.robot-avatar :deep(svg),
.avatar-ai :deep(svg) {
  display: block;
}

.avatar-user {
  background: rgba(22, 24, 29, 0.05);
  color: var(--text-secondary);
  box-shadow: inset 0 0 0 1px var(--line-soft);
}

.icon-btn,
.sb-mini-expand {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  padding: 4px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-tertiary);
  transition:
    background 0.15s,
    color 0.15s;
}

.icon-btn:hover,
.sb-mini-expand:hover {
  background: transparent;
  color: var(--text-primary);
}

.sb-new-wrap,
.sb-search-wrap {
  padding-left: 18px;
  padding-right: 18px;
}

.sb-new-btn,
.sb-submit-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  padding: 14px 0;
  border: none;
  border-top: 1px solid var(--line-soft);
  border-bottom: 1px solid var(--line-default);
  border-radius: 0;
  background: transparent;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 550;
  letter-spacing: 0.02em;
  font-family: inherit;
  cursor: pointer;
  transition: color 0.15s;
}

.sb-new-btn:hover,
.sb-submit-btn:hover {
  background: transparent;
  color: var(--accent-blue);
}

.sb-search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border: none;
  border-bottom: 1px solid var(--line-default);
  border-radius: 0;
  background: transparent;
}

.sb-search-box:focus-within {
  border-color: var(--accent-blue);
}

.sb-search-icon,
.sb-search-clear {
  color: var(--text-tertiary);
}

.sb-search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 12.5px;
  font-family: inherit;
  color: var(--text-primary);
  min-width: 0;
}

.sb-search-input::placeholder {
  color: var(--text-tertiary);
}

.sb-search-clear {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 0 2px;
}

.sb-search-clear:hover {
  color: var(--text-primary);
}

.sb-sidebar-section {
  padding: 14px 18px;
}

.sb-section-toggle {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 0 4px 10px;
  border: none;
  background: none;
  cursor: pointer;
}

.sb-section-body {
  padding-bottom: 10px;
  max-height: 60vh;
  overflow-y: auto;
}

.sb-section-chevron {
  color: var(--text-tertiary);
  transition: transform 0.16s ease;
  justify-self: end;
}

.sb-section-toggle.open .sb-section-chevron {
  transform: rotate(180deg);
}

.sb-section-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
  line-height: 1;
  text-align: left;
}

.sb-item-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.sb-item {
  flex: 1;
  text-align: left;
  background: none;
  border: none;
  font-family: inherit;
  font-size: 13px;
  color: var(--text-secondary);
  padding: 10px 0 10px 14px;
  border-radius: 0;
  cursor: pointer;
  display: block;
  transition: color 0.14s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.5;
  position: relative;
}

.sb-item::before {
  content: "";
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 1px;
  background: transparent;
  transition:
    background 0.18s ease,
    width 0.18s ease;
}

.sb-item:hover {
  background: transparent;
  color: var(--text-primary);
}

.sb-item.active {
  background: transparent;
  color: var(--accent-blue);
  font-weight: 600;
}

.sb-item.active::before {
  width: 2px;
  background: var(--accent-blue);
}

.sb-item-delete {
  flex-shrink: 0;
  display: none;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: 4px;
  transition: color 0.14s, background 0.14s;
  padding: 0;
}

.sb-item-wrapper:hover .sb-item-delete {
  display: inline-flex;
}

.sb-item-delete:hover {
  color: var(--accent-danger);
  background: var(--accent-danger-soft);
}

.sb-empty {
  padding: 8px 0;
  color: var(--text-tertiary);
  font-size: 12.5px;
}

.sb-mini {
  padding-top: 18px;
}

.sb-mini-divider {
  width: 28px;
  height: 1px;
  background: var(--line-soft);
}

.sb-mini-dot {
  width: auto;
  height: auto;
  padding: 6px 0 4px;
  border-radius: 0;
  background: transparent;
  color: var(--text-tertiary);
  border: none;
  border-bottom: 1px solid var(--line-soft);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

#main {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  position: relative;
  z-index: 10;
}

#topbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--line-soft);
  background: rgba(251, 250, 247, 0.72);
  backdrop-filter: blur(24px);
  gap: 12px;
}

.topbar-left,
.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.topbar-right {
  gap: 18px;
}

.exp-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.exp-title svg {
  color: var(--accent-blue);
}

.topbar-user {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 30px;
  line-height: 1;
  color: var(--text-tertiary);
}

.topbar-user svg {
  display: block;
  flex-shrink: 0;
}

.topbar-logout-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
  margin-left: 4px;
}

.topbar-logout-btn:hover {
  background: color-mix(in srgb, var(--accent-blue) 8%, transparent);
  color: var(--accent-blue);
}

#initialState {
  min-height: calc(100vh - 132px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow-y: auto;
  padding: 24px 32px 48px;
}

.init-hero {
  text-align: center;
  padding-top: 0;
  margin-bottom: 28px;
}

.init-hero h1 {
  margin-bottom: 12px;
  font-size: 44px;
  font-family:
    "Snell Roundhand",
    "Segoe Script",
    "Brush Script MT",
    "Lucida Handwriting",
    "Apple Chancery",
    cursive;
  font-weight: 500;
  font-style: italic;
  letter-spacing: 0.01em;
  color: var(--text-primary);
}

.init-subtitle {
  font-size: 24px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.init-desc {
  max-width: 620px;
  margin: 0 auto;
  font-size: 14px;
  color: var(--text-tertiary);
  line-height: 1.9;
}

.init-card-wrap {
  max-width: 680px;
  width: min(680px, 100%);
  margin-top: 0;
  margin-bottom: 20px;
}

.init-input-shell,
.bottom-card {
  position: relative;
  padding: 18px 20px 16px;
  background: rgba(251, 250, 247, 0.48);
  border: none;
  border-radius: 24px;
  box-shadow: 0 8px 32px -12px rgba(29, 36, 48, 0.12);
  backdrop-filter: blur(24px);
  overflow: hidden;
  transition:
    box-shadow 0.3s ease,
    background 0.3s ease;
}

.init-input-shell.focused,
.bottom-card.focused {
  box-shadow: 0 12px 40px -14px rgba(29, 36, 48, 0.18);
  background: rgba(251, 250, 247, 0.58);
}

.init-glow-orb,
.bottom-glow-orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(60px);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.5s ease;
}

.init-input-shell.focused .init-glow-orb,
.bottom-card.focused .bottom-glow-orb {
  opacity: 1;
}

.init-glow-blue,
.bottom-glow-blue {
  width: 200px;
  height: 200px;
  top: -60px;
  left: -40px;
  background: var(--accent-blue);
  opacity: 0;
}

.init-input-shell.focused .init-glow-blue,
.bottom-card.focused .bottom-glow-blue {
  opacity: 0.08;
}

.init-glow-amber {
  width: 160px;
  height: 160px;
  bottom: -50px;
  right: -30px;
  background: var(--accent-amber);
  opacity: 0;
}

.init-input-shell.focused .init-glow-amber {
  opacity: 0.06;
}

.init-input-shell::before {
  content: "";
  position: absolute;
  left: 0;
  top: 14px;
  bottom: 14px;
  width: 2px;
  border-radius: 999px;
  background: linear-gradient(180deg, var(--accent-blue), var(--accent-amber));
  opacity: 0.72;
}

.init-input-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.init-input-label :deep(svg) {
  color: var(--accent-blue);
}

.init-input-shell textarea,
.bottom-card textarea {
  width: 100%;
  resize: none;
  font-size: 13px;
  color: var(--text-primary);
  font-family: inherit;
  outline: none;
  line-height: 1.65;
  background: transparent;
  border: none;
  border-radius: 0;
}

.init-input-shell textarea {
  min-height: 84px;
  padding: 0 52px 0 0;
  font-size: 15px;
}

.init-input-shell textarea::placeholder {
  color: color-mix(in srgb, var(--text-tertiary) 92%, white);
}

.init-input-shell textarea:focus {
  outline: none;
}

.bottom-card textarea {
  padding: 14px 52px 12px 0;
  border: none;
  border-radius: 0;
}

.bottom-card textarea:focus {
  outline: none;
}

.focus-ring,
.focus-ring-bottom {
  position: absolute;
  inset: -1px;
  border-radius: 24px;
  pointer-events: none;
  border: 2px solid color-mix(in srgb, var(--accent-blue) 28%, transparent);
  box-shadow: 0 0 16px -4px color-mix(in srgb, var(--accent-blue) 24%, transparent);
}

.focus-ring-bottom {
  border-radius: 24px;
  inset: -1px;
}

.ring-fade-enter-active {
  transition: opacity 0.25s ease;
}

.ring-fade-leave-active {
  transition: opacity 0.18s ease;
}

.ring-fade-enter-from,
.ring-fade-leave-to {
  opacity: 0;
}

.init-input-shell .send-circle {
  position: absolute;
  bottom: 16px;
  right: 16px;
}

.bottom-card .send-circle {
  position: absolute;
  bottom: 14px;
  right: 16px;
}

.send-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, var(--text-primary), #243149);
  color: var(--text-inverse);
  cursor: pointer;
  box-shadow: var(--shadow-soft);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    filter 0.18s ease,
    background 0.18s ease,
    opacity 0.18s ease;
}

.send-circle:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px -16px rgba(29, 36, 48, 0.48);
  filter: brightness(1.04);
}

.send-circle:disabled {
  background: rgba(22, 24, 29, 0.1);
  color: rgba(22, 24, 29, 0.28);
  cursor: not-allowed;
  box-shadow: none;
}

#activeState {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

#msgScroll {
  flex: 1;
  overflow-y: auto;
  padding: 34px 56px 32px 32px;
}

#msgList {
  max-width: 1140px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.msg-row {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.msg-row.user-row {
  justify-content: flex-end;
}

.bubble-user {
  position: relative;
  max-width: 72%;
  padding: 14px 20px 14px 18px;
  border-radius: 20px 20px 4px 20px;
  background: linear-gradient(90deg, rgba(62, 111, 230, 0.08), rgba(62, 111, 230, 0.03));
  color: var(--text-primary);
  box-shadow: none;
  font-size: 13.5px;
  line-height: 1.7;
}

.bubble-user::after {
  content: "";
  position: absolute;
  right: 0;
  top: 10px;
  bottom: 10px;
  width: 2px;
  border-radius: 999px;
  background: var(--accent-blue);
  opacity: 0.56;
}

.bubble-ai-wrap {
  flex: 1;
  max-width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bubble-ai,
.typing-bubble {
  background: transparent;
  border: none;
  box-shadow: none;
}

.bubble-ai {
  position: relative;
  padding: 0 0 0 22px;
  border-radius: 0;
  color: var(--text-primary);
  font-size: 13.5px;
  line-height: 1.75;
}

.bubble-ai::before {
  content: "";
  position: absolute;
  left: 0;
  top: 4px;
  bottom: 4px;
  width: 1px;
  background: linear-gradient(180deg, var(--accent-blue), var(--line-soft));
}

.bubble-ai :deep(p) {
  margin: 0 0 5px;
}

.bubble-ai :deep(p:last-child) {
  margin-bottom: 0;
}

.bubble-markdown {
  max-width: 100% !important;
}

.bubble-markdown :deep(h2) {
  font-size: 16px;
  font-weight: 700;
  margin: 16px 0 8px;
  color: var(--text-primary);
}

.bubble-markdown :deep(h2:first-child) {
  margin-top: 0;
}

.bubble-markdown :deep(h3) {
  font-size: 14px;
  font-weight: 600;
  margin: 12px 0 6px;
  color: var(--text-primary);
}

.bubble-markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
  font-size: 12.5px;
}

.bubble-markdown :deep(th) {
  text-align: left;
  padding: 8px 10px;
  background: color-mix(in srgb, var(--accent-blue) 8%, transparent);
  border-bottom: 2px solid var(--line-soft);
  font-weight: 600;
  color: var(--text-primary);
  font-size: 11.5px;
}

.bubble-markdown :deep(td) {
  padding: 7px 10px;
  border-bottom: 1px solid var(--line-soft);
  color: var(--text-secondary);
  vertical-align: top;
}

.bubble-markdown :deep(tr:hover td) {
  background: color-mix(in srgb, var(--accent-blue) 4%, transparent);
}

.bubble-markdown :deep(ul),
.bubble-markdown :deep(ol) {
  margin: 6px 0;
  padding-left: 20px;
}

.bubble-markdown :deep(li) {
  margin: 3px 0;
  color: var(--text-secondary);
}

.bubble-markdown :deep(strong) {
  color: var(--text-primary);
  font-weight: 400;
  background: color-mix(in srgb, var(--accent-blue) 8%, transparent);
  padding: 1px 4px;
  border-radius: 3px;
}

.bubble-markdown :deep(em) {
  font-style: normal;
  color: var(--text-primary);
  font-weight: 400;
  background: color-mix(in srgb, var(--accent-blue) 8%, transparent);
  padding: 1px 4px;
  border-radius: 3px;
}

.bubble-markdown :deep(strong em),
.bubble-markdown :deep(em strong) {
  font-weight: 400;
  font-style: normal;
  color: var(--text-primary);
  background: color-mix(in srgb, var(--accent-blue) 12%, transparent);
  padding: 1px 4px;
  border-radius: 3px;
}

.bubble-markdown :deep(blockquote) {
  margin: 8px 0;
  padding: 6px 12px;
  border-left: 3px solid var(--accent-blue);
  background: color-mix(in srgb, var(--accent-blue) 5%, transparent);
  border-radius: 0 6px 6px 0;
}

.bubble-markdown :deep(blockquote p) {
  margin: 0;
  color: var(--text-secondary);
  font-style: normal;
  font-family:
    "Noto Serif SC",
    "Source Han Serif SC",
    "STSong",
    "SimSun",
    serif;
}

.bubble-markdown :deep(blockquote strong),
.bubble-markdown :deep(blockquote em),
.bubble-markdown :deep(blockquote strong em),
.bubble-markdown :deep(blockquote em strong) {
  background: none;
  padding: 0;
  font-family:
    "Noto Serif SC",
    "Source Han Serif SC",
    "STSong",
    "SimSun",
    serif;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line-soft);
}

.step-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent-blue) 10%, transparent);
  color: var(--accent-blue);
  font-size: 10px;
  font-weight: 700;
  font-family: var(--font-mono);
  letter-spacing: 0.08em;
}

.step-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.step-body {
  font-size: 13px;
  line-height: 1.75;
  color: var(--text-secondary);
}

.step-body :deep(p) {
  margin: 0 0 5px;
}

.step-body :deep(p:last-child) {
  margin-bottom: 0;
}

.step-interact {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--line-soft);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.step-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.step-options-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.4);
  color: var(--text-tertiary);
  font-size: 12.5px;
}

.step-opt-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid var(--line-default);
  background: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    box-shadow 0.15s ease;
  font-family: inherit;
  text-align: left;
  width: 100%;
}

.step-opt-btn:hover {
  background: color-mix(in srgb, var(--accent-blue) 8%, white);
  border-color: color-mix(in srgb, var(--accent-blue) 30%, var(--line-default));
  box-shadow: 0 2px 8px -4px color-mix(in srgb, var(--accent-blue) 20%, transparent);
}

.step-opt-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 7px;
  background: color-mix(in srgb, var(--accent-blue) 10%, transparent);
  color: var(--accent-blue);
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono);
  flex-shrink: 0;
}

.step-opt-label {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.4;
}

.step-other-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.step-other-input {
  flex: 1;
  padding: 8px 12px;
  border-radius: 12px;
  border: 1px solid var(--line-default);
  background: rgba(255, 255, 255, 0.5);
  font-size: 12.5px;
  font-family: inherit;
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.15s ease;
}

.step-other-input::placeholder {
  color: var(--text-tertiary);
}

.step-other-input:focus {
  border-color: color-mix(in srgb, var(--accent-blue) 40%, var(--line-default));
}

.step-other-submit {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, var(--text-primary), #243149);
  color: var(--text-inverse);
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity 0.15s ease;
}

.step-other-submit:disabled {
  background: rgba(22, 24, 29, 0.1);
  color: rgba(22, 24, 29, 0.28);
  cursor: not-allowed;
}

.step-skip-btn {
  align-self: flex-start;
  padding: 4px 10px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  font-size: 11px;
  cursor: pointer;
  transition: color 0.15s ease;
  font-family: inherit;
}

.step-skip-btn:hover {
  color: var(--text-secondary);
}

.step-answer {
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--accent-blue) 6%, transparent);
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}

.step-answer-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--accent-blue);
  flex-shrink: 0;
}

.step-answer-text {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.5;
  flex: 1;
  min-width: 0;
}

.step-answer-skipped {
  color: var(--text-tertiary);
  font-style: italic;
}

.step-rewrite-btn {
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid var(--line-default);
  background: transparent;
  color: var(--text-tertiary);
  font-size: 10px;
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease;
  font-family: inherit;
  flex-shrink: 0;
}

.step-rewrite-btn:hover {
  color: var(--accent-blue);
  border-color: color-mix(in srgb, var(--accent-blue) 30%, var(--line-default));
}

.step-rewrite-row {
  display: flex;
  gap: 6px;
  align-items: center;
  width: 100%;
}

.step-rewrite-confirm,
.step-rewrite-cancel {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s ease;
}

.step-rewrite-confirm {
  background: color-mix(in srgb, var(--accent-blue) 12%, transparent);
  color: var(--accent-blue);
}

.step-rewrite-confirm:hover {
  background: color-mix(in srgb, var(--accent-blue) 20%, transparent);
}

.step-rewrite-cancel {
  background: rgba(0, 0, 0, 0.05);
  color: var(--text-tertiary);
}

.step-rewrite-cancel:hover {
  background: rgba(0, 0, 0, 0.1);
  color: var(--text-secondary);
}

.step-badge-final {
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-amber));
  color: white;
}

.step-supplement .step-header {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
}

.typing-bubble {
  position: relative;
  padding: 0 0 0 22px;
  border-radius: 0;
}

.typing-bubble::before {
  content: "";
  position: absolute;
  left: 0;
  top: 4px;
  bottom: 4px;
  width: 1px;
  background: linear-gradient(180deg, var(--accent-blue), var(--line-soft));
}

.dots {
  display: flex;
  gap: 4px;
  align-items: center;
  height: 14px;
}

.dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent-amber);
  animation: pulse 1.2s ease-in-out infinite;
}

.dot:nth-child(2) {
  animation-delay: 0.2s;
}

.dot:nth-child(3) {
  animation-delay: 0.4s;
}

#bottomBar {
  flex-shrink: 0;
  padding: 14px 56px 16px 32px;
}

.bottom-inner {
  max-width: 860px;
  margin: 0 auto;
}



#toast {
  position: fixed;
  bottom: 28px;
  right: 28px;
  background: rgba(251, 250, 247, 0.94);
  border: none;
  border-left: 2px solid var(--accent-blue);
  border-radius: 18px 18px 18px 6px;
  box-shadow: var(--shadow-soft);
  padding: 14px 20px;
  z-index: 999;
  opacity: 0;
  transform: translateY(10px);
  pointer-events: none;
  transition:
    opacity 0.22s,
    transform 0.22s;
  min-width: 220px;
  max-width: 360px;
}

#toast.show {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}

#toast-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

#toast-desc {
  font-size: 11.5px;
  color: var(--text-secondary);
  line-height: 1.5;
  word-break: break-word;
}

.state-swap-enter-active,
.state-swap-leave-active {
  transition:
    opacity 0.24s ease,
    transform 0.24s ease;
}

.state-swap-enter-from,
.state-swap-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

@keyframes pulse {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.7;
  }

  30% {
    transform: translateY(-5px);
    opacity: 1;
  }
}

@media (max-width: 960px) {
  #sidebar {
    width: 56px;
    min-width: 56px;
  }

  #sidebar .sb-full {
    display: none;
  }

  #sidebar .sb-mini {
    display: flex;
  }

  #main {
    min-width: 0;
  }

  .topbar-user {
    display: none;
  }

  #topbar,
  #bottomBar,
  #msgScroll,
  #initialState {
    padding-left: 18px;
    padding-right: 18px;
  }

  .locked-chat-page::after {
    inset: 10px;
  }
}

@media (max-width: 640px) {
  #initialState {
    min-height: auto;
    justify-content: flex-start;
    padding-top: 8px;
  }

  .init-input-shell {
    padding: 12px 14px 10px 16px;
  }

  .init-input-shell textarea {
    min-height: 76px;
  }
}
</style>
