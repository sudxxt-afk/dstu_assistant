<script setup>
import { ref, onMounted } from "vue";
import { api } from "../api";
import Icon from "../components/Icon.vue";

const tasks = ref([]);
const showDone = ref(false);
const title = ref("");
const due = ref("");

async function load() {
  tasks.value = await api.get(`/tasks?include_done=${showDone.value}`);
}
async function add() {
  if (!title.value.trim()) return;
  await api.post("/tasks", { title: title.value.trim(), due_date: due.value || null });
  title.value = "";
  due.value = "";
  load();
}
async function toggle(t) {
  await api.patch(`/tasks/${t.id}/toggle`);
  load();
}
async function del(t) {
  await api.del(`/tasks/${t.id}`);
  load();
}
const dm = (s) => (s ? s.slice(8, 10) + "." + s.slice(5, 7) : "");

onMounted(load);
</script>

<template>
  <div class="head spread">
    <h1 class="t-h1">Задачи</h1>
    <label class="chk">
      <input type="checkbox" v-model="showDone" @change="load" />
      <span class="muted">выполненные</span>
    </label>
  </div>

  <form class="addbar" @submit.prevent="add">
    <input v-model="title" placeholder="Новая задача…" />
    <input v-model="due" type="date" class="mono due" />
    <button class="btn btn-primary"><Icon name="plus" :size="16" /></button>
  </form>

  <div v-if="!tasks.length" class="empty">Задач нет</div>
  <div v-else class="list">
    <div v-for="t in tasks" :key="t.id" class="task" :class="{ done: t.done }">
      <button class="checkbox" :class="{ 'is-checked': t.done }" @click="toggle(t)">
        <Icon v-if="t.done" name="check" :size="13" />
      </button>
      <div class="ttl">{{ t.title }}</div>
      <div v-if="t.due_date" class="due-tag mono">{{ dm(t.due_date) }}</div>
      <button class="icon-btn sm danger" @click="del(t)"><Icon name="trash" :size="15" /></button>
    </div>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}
.chk {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  cursor: pointer;
}
.chk input {
  width: auto;
  height: auto;
}
.addbar {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-5);
}
.due {
  max-width: 150px;
}
.task {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-1);
  border-bottom: 1px solid var(--color-border);
}
.ttl {
  font-size: var(--text-base);
}
.task.done .ttl {
  color: var(--color-text-tertiary);
  text-decoration: line-through;
}
.due-tag {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

@media (max-width: 759px) {
  .addbar {
    flex-wrap: wrap;
  }
  .addbar > input:first-child {
    flex: 1 1 100%;
  }
  .due {
    max-width: none;
    flex: 1;
  }
}
</style>
