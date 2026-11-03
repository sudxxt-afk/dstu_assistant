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
      <div class="brand">
        <span class="word">dstu<span class="dim"> assistant</span></span>
      </div>
      <nav>
        <router-link v-for="n in nav" :key="n.to" :to="n.to" class="nav-item">
          <Icon :name="n.icon" :size="18" />
          <span>{{ n.label }}</span>
        </router-link>
      </nav>
      <div class="foot">
        <div v-if="week" class="weekcard">
          <div class="t-eyebrow">Учебная неделя</div>
          <div class="wnum">{{ week }}</div>
          <div class="wpar">{{ parity }}</div>
        </div>
        <button class="logout" @click="logout">
          <Icon name="logout" :size="15" /> Выйти
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
  padding: var(--space-10) var(--page-pad) var(--space-12);
  max-width: var(--content-max);
  animation: rise var(--dur-med) var(--ease-out);
}
@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
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
    background: var(--color-surface);
    border-right: 1px solid var(--color-border);
    padding: var(--space-6) var(--space-4);
  }
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--space-2) var(--space-6);
}
.word {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
}
nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 10px var(--space-3);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--text-base);
  font-weight: var(--weight-medium);
  transition: color var(--dur-fast) var(--ease-standard),
    background var(--dur-fast) var(--ease-standard);
}
.nav-item:hover {
  color: var(--color-text);
  background: var(--color-surface-hover);
}
.nav-item.router-link-active {
  color: var(--color-accent);
  background: var(--color-accent-soft);
  font-weight: var(--weight-semibold);
}
.foot {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.weekcard {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: end;
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-sunken);
  row-gap: 2px;
}
.weekcard .t-eyebrow {
  grid-column: 1 / -1;
}
.wnum {
  font-family: var(--font-display);
  font-size: var(--text-3xl);
  font-weight: var(--weight-semibold);
  line-height: 1;
  letter-spacing: var(--tracking-tight);
}
.wpar {
  font-size: var(--text-xs);
  color: var(--color-accent);
  font-weight: var(--weight-semibold);
  padding-bottom: 4px;
}
.logout {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--space-2);
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
  left: max(var(--space-3), env(safe-area-inset-left, 0px));
  right: max(var(--space-3), env(safe-area-inset-right, 0px));
  bottom: calc(var(--space-3) + env(safe-area-inset-bottom, 0px));
  justify-content: space-around;
  gap: var(--space-1);
  padding: var(--space-2);
  background: color-mix(in srgb, var(--color-surface) 88%, transparent);
  backdrop-filter: blur(16px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  z-index: var(--z-nav);
}
.tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  flex: 1;
  padding: 6px 2px;
  border-radius: var(--radius-md);
  color: var(--color-text-tertiary);
  font-size: var(--text-2xs);
  font-weight: var(--weight-medium);
  transition: color var(--dur-fast) var(--ease-standard),
    background var(--dur-fast) var(--ease-standard);
}
.tab.router-link-active {
  color: var(--color-accent);
  background: var(--color-accent-soft);
}

@media (max-width: 759px) {
  .tabbar {
    display: flex;
    flex-direction: row;
  }
  .content {
    padding: calc(var(--space-5) + env(safe-area-inset-top, 0px)) var(--space-4)
      calc(96px + env(safe-area-inset-bottom, 0px));
  }
}
</style>
