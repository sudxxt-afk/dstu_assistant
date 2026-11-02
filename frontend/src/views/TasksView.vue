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
  await api.post("/tasks", {
    title: title.value.trim(),
    due_date: due.value || null,
  });
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
    <h1>Задачи</h1>
    <label class="chk">
      <input type="checkbox" v-model="showDone" @change="load" />
      <span class="muted">показывать выполненные</span>
    </label>
  </div>

  <form class="addbar" @submit.prevent="add">
    <input v-model="title" placeholder="Новая задача…" />
    <input v-model="due" type="date" class="mono due" />
    <button class="btn btn-primary"><Icon name="plus" :size="16" /></button>
  </form>

  <div v-if="!tasks.length" class="empty dim">Задач нет</div>
  <div v-else class="list">
    <div v-for="t in tasks" :key="t.id" class="task" :class="{ done: t.done }">
      <button class="box" :class="{ on: t.done }" @click="toggle(t)">
        <Icon v-if="t.done" name="check" :size="13" />
      </button>
      <div class="ttl">{{ t.title }}</div>
      <div v-if="t.due_date" class="due-tag mono">{{ dm(t.due_date) }}</div>
      <button class="del" @click="del(t)"><Icon name="trash" :size="15" /></button>
    </div>
  </div>
</template>

<style scoped>
.head {
  margin-bottom: 20px;
}
h1 {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.02em;
}
.chk {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  cursor: pointer;
}
.chk input {
  width: auto;
  height: auto;
}
.addbar {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}
.due {
  max-width: 150px;
}
.list {
  display: flex;
  flex-direction: column;
}
.task {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: 12px;
  padding: 12px 4px;
  border-bottom: 1px solid var(--line);
}
.box {
  width: 18px;
  height: 18px;
  border: 1.5px solid var(--line-strong);
  border-radius: 4px;
  display: grid;
  place-items: center;
  color: var(--accent-fg);
  transition: all 0.12s var(--ease);
}
.box:hover {
  border-color: var(--accent);
}
.box.on {
  background: var(--accent);
  border-color: var(--accent);
}
.ttl {
  font-size: 14px;
}
.task.done .ttl {
  color: var(--fg-3);
  text-decoration: line-through;
}
.due-tag {
  font-size: 12px;
  color: var(--fg-2);
}
.del {
  color: var(--fg-3);
  display: flex;
  padding: 4px;
}
.del:hover {
  color: var(--danger);
}
.empty {
  padding: 24px 0;
}
</style>
