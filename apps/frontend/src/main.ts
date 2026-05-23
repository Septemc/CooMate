import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import { useChatStore } from "./stores/chat";
import "./style.css";

async function bootstrap() {
  const app = createApp(App);
  const pinia = createPinia();

  app.use(pinia);

  const chatStore = useChatStore(pinia);
  const savedUser = localStorage.getItem("coomate-user");
  const savedToken = localStorage.getItem("coomate-token");
  if (savedUser && savedToken) {
    try {
      const user = JSON.parse(savedUser);
      chatStore.setAuth(savedToken, user);
    } catch {}
  }

  app.use(router);
  app.mount("#app");
}

void bootstrap();
