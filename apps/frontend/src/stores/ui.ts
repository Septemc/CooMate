import { defineStore } from "pinia";
import { ref } from "vue";

export const useUIStore = defineStore("ui", () => {
  const leftSidebarOpen = ref(localStorage.getItem("coomate-left-sidebar") !== "closed");
  const rightSidebarOpen = ref(localStorage.getItem("coomate-right-sidebar") !== "closed");

  function toggleLeftSidebar() {
    leftSidebarOpen.value = !leftSidebarOpen.value;
    localStorage.setItem("coomate-left-sidebar", leftSidebarOpen.value ? "open" : "closed");
  }

  function toggleRightSidebar() {
    rightSidebarOpen.value = !rightSidebarOpen.value;
    localStorage.setItem("coomate-right-sidebar", rightSidebarOpen.value ? "open" : "closed");
  }

  return {
    leftSidebarOpen,
    rightSidebarOpen,
    toggleLeftSidebar,
    toggleRightSidebar,
  };
});
