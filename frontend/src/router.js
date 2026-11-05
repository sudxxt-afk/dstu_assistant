import { createRouter, createWebHashHistory } from "vue-router";
import { getToken } from "./api";

const routes = [
  { path: "/login", component: () => import("./views/TokenGate.vue") },
  { path: "/", redirect: "/schedule" },
  { path: "/schedule", component: () => import("./views/ScheduleView.vue") },
  { path: "/tasks", component: () => import("./views/TasksView.vue") },
  { path: "/lectures", component: () => import("./views/LecturesView.vue") },
  { path: "/editor", component: () => import("./views/EditorView.vue") },
  { path: "/settings", component: () => import("./views/SettingsView.vue") },
];

const router = createRouter({ history: createWebHashHistory(), routes });

router.beforeEach((to) => {
  if (to.path !== "/login" && !getToken()) return "/login";
  if (to.path === "/login" && getToken()) return "/schedule";
});

export default router;
