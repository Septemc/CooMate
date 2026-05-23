import { createRouter, createWebHistory } from "vue-router";
import LandingView from "../views/LandingView.vue";
import ChatView from "../views/ChatView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "landing",
      component: LandingView
    },
    {
      path: "/chat",
      name: "chat",
      component: ChatView
    }
  ]
});

export default router;
