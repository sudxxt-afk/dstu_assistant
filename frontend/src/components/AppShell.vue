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

onMounted(async () => {
  try {
    const d = await api.get("/schedule/day");
    week.value = d.week_number;
    parity.value = d.parity === "odd" ? "нечётная" : "чётная";
  } catch (e) {
    if (e.status === 401) {
      clearAuth();
      router.push("/login");
    }
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
        <button class="logout" @click="clearAuth(); router.push('/login')">
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
  padding: 28px 32px 32px;
  max-width: 1040px;
}

/* ---------- боковое меню (десктоп) ---------- */
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
    border-right: 1px solid var(--line);
    padding: 20px 14px;
  }
}

.brand {
  font-weight: 700;
  font-size: 16px;
  letter-spacing: -0.01em;
  padding: 6px 10px 20px;
}
nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  color: var(--fg-2);
  font-size: 13.5px;
  font-weight: 500;
  transition: color 0.12s var(--ease), background 0.12s var(--ease);
}
.nav-item:hover {
  color: var(--fg);
  background: var(--surface);
}
.nav-item.router-link-active {
  color: var(--accent);
  background: var(--accent-soft);
}
.foot {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
}
.week {
  font-size: 12px;
  color: var(--fg-3);
}
.logout {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: var(--fg-3);
  transition: color 0.12s var(--ease);
}
.logout:hover {
  color: var(--danger);
}

/* ---------- нижняя навигация (только мобила) ---------- */
.tabbar {
  display: none; /* на десктопе скрыта; показывается только на узком экране */
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  justify-content: space-around;
  background: color-mix(in srgb, var(--bg) 90%, transparent);
  backdrop-filter: blur(12px);
  border-top: 1px solid var(--line);
  padding: 7px 0 calc(6px + env(safe-area-inset-bottom));
  z-index: 10;
}
.tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  flex: 1;
  padding: 4px 2px;
  color: var(--fg-3);
  font-size: 10px;
  font-weight: 500;
  transition: color 0.12s var(--ease);
}
.tab.router-link-active {
  color: var(--accent);
}

@media (max-width: 759px) {
  .tabbar {
    display: flex;
  }
  .content {
    padding: calc(16px + env(safe-area-inset-top)) 16px
      calc(74px + env(safe-area-inset-bottom));
  }
}
</style>
