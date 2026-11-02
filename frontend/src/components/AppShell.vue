<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { api, clearAuth } from "../api";
import Icon from "./Icon.vue";

const router = useRouter();
const week = ref(null);
const parity = ref("");

const nav = [
  { to: "/schedule", icon: "calendar", label: "Расписание" },
  { to: "/tasks", icon: "tasks", label: "Задачи" },
  { to: "/editor", icon: "editor", label: "Редактор" },
  { to: "/settings", icon: "settings", label: "Настройки" },
];

function logout() {
  clearAuth();
  router.push("/login");
}

onMounted(async () => {
  try {
    const d = await api.get("/schedule/day");
    week.value = d.week_number;
    parity.value = d.parity === "odd" ? "нечётная" : "чётная";
  } catch (e) {
    if (e.status === 401) logout();
  }
});
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">dstu<span class="dim">/assistant</span></div>
      <nav>
        <router-link v-for="n in nav" :key="n.to" :to="n.to" class="nav-item">
          <Icon :name="n.icon" :size="17" />
          <span>{{ n.label }}</span>
        </router-link>
      </nav>
      <div class="foot">
        <div v-if="week" class="week mono">W{{ week }} · {{ parity }}</div>
        <button class="logout" @click="logout">
          <Icon name="logout" :size="15" /> выйти
        </button>
      </div>
    </aside>

    <main class="content"><slot /></main>

    <nav class="tabbar">
      <router-link v-for="n in nav" :key="n.to" :to="n.to" class="tab">
        <Icon :name="n.icon" :size="21" />
        <span>{{ n.label }}</span>
      </router-link>
    </nav>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100%;
}
.sidebar {
  display: none;
}
.content {
  padding: var(--space-8) var(--page-pad) var(--space-8);
  max-width: var(--content-max);
}

@media (min-width: 760px) {
  .shell {
    display: grid;
    grid-template-columns: var(--sidebar-w) 1fr;
  }
  .sidebar {
    display: flex;
    flex-direction: column;
    position: sticky;
    top: 0;
    height: 100vh;
    border-right: 1px solid var(--color-border);
    padding: var(--space-5) var(--space-3);
  }
}

.brand {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-tight);
  padding: var(--space-2) var(--space-3) var(--space-5);
}
nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  transition: color var(--dur-fast) var(--ease-standard),
    background var(--dur-fast) var(--ease-standard);
}
.nav-item:hover {
  color: var(--color-text);
  background: var(--color-surface);
}
.nav-item.router-link-active {
  color: var(--color-accent);
  background: var(--color-accent-soft);
}
.foot {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-3);
}
.week {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}
.logout {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  transition: color var(--dur-fast) var(--ease-standard);
}
.logout:hover {
  color: var(--color-danger);
}

/* нижняя навигация — только мобила */
.tabbar {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  justify-content: space-around;
  background: color-mix(in srgb, var(--color-canvas) 90%, transparent);
  backdrop-filter: blur(12px);
  border-top: 1px solid var(--color-border);
  padding: var(--space-2) 0 calc(var(--space-2) + env(safe-area-inset-bottom));
  z-index: var(--z-nav);
}
.tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  flex: 1;
  padding: var(--space-1) 2px;
  color: var(--color-text-tertiary);
  font-size: var(--text-2xs);
  font-weight: var(--weight-medium);
  transition: color var(--dur-fast) var(--ease-standard);
}
.tab.router-link-active {
  color: var(--color-accent);
}

@media (max-width: 759px) {
  .tabbar {
    display: flex;
  }
  .content {
    padding: calc(var(--space-4) + env(safe-area-inset-top)) var(--space-4)
      calc(74px + env(safe-area-inset-bottom));
  }
}
</style>
