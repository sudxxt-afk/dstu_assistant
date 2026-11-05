<script setup>
import { ref, computed, onMounted } from "vue";
import { api } from "../api";
import Icon from "../components/Icon.vue";

const tasks = ref([]);
const subjects = ref([]);
const showDone = ref(false);
const title = ref("");
const due = ref("");
const subjectId = ref("");
const important = ref(false);

async function load() {
  tasks.value = await api.get(`/tasks?include_done=${showDone.value}`);
}
async function loadSubjects() {
  subjects.value = await api.get("/subjects");
}
async function add() {
  if (!title.value.trim()) return;
  await api.post("/tasks", {
    title: title.value.trim(),
    due_date: due.value || null,
    subject_id: subjectId.value ? Number(subjectId.value) : null,
    priority: important.value ? 1 : 0,
  });
  title.value = "";
  due.value = "";
  subjectId.value = "";
  important.value = false;
  load();
}
async function toggle(t) {
  await api.patch(`/tasks/${t.id}/toggle`);
  load();
}
async function togglePrio(t) {
  await api.patch(`/tasks/${t.id}`, { priority: t.priority ? 0 : 1 });
  load();
}
async function del(t) {
  await api.del(`/tasks/${t.id}`);
  load();
}

const todayIso = new Date().toISOString().slice(0, 10);
const tomorrowIso = new Date(Date.now() + 864e5).toISOString().slice(0, 10);
const overdue = (t) => !t.done && t.due_date && t.due_date < todayIso;
const dm = (s) => (s ? s.slice(8, 10) + "." + s.slice(5, 7) : "");

function bucketOf(t) {
  if (t.done) return "Выполнено";
  if (!t.due_date) return "Без срока";
  if (t.due_date < todayIso) return "Просрочено";
  if (t.due_date === todayIso) return "Сегодня";
  if (t.due_date === tomorrowIso) return "Завтра";
  return "Позже";
}
const ORDER = ["Просрочено", "Сегодня", "Завтра", "Позже", "Без срока", "Выполнено"];
const groups = computed(() => {
  const map = {};
  for (const t of tasks.value) (map[bucketOf(t)] ||= []).push(t);
  return ORDER.filter((k) => map[k]?.length).map((k) => ({ name: k, items: map[k] }));
});
const activeCount = computed(() => tasks.value.filter((t) => !t.done).length);

onMounted(() => {
  load();
  loadSubjects();
});
</script>

<template>
  <div class="page-head">
    <div>
      <h1 class="t-h1">Задачи</h1>
      <div v-if="tasks.length" class="muted sub">{{ activeCount }} в работе</div>
    </div>
    <label class="chk">
      <input type="checkbox" v-model="showDone" @change="load" />
      <span>Показать выполненные</span>
    </label>
  </div>

  <form class="addbar card" @submit.prevent="add">
    <input v-model="title" class="addin" placeholder="Что нужно сделать?" aria-label="Новая задача" />
    <select v-model="subjectId" class="sel" aria-label="Предмет">
      <option value="">Без предмета</option>
      <option v-for="su in subjects" :key="su.id" :value="su.id">{{ su.name }}</option>
    </select>
    <input v-model="due" type="date" class="mono due" aria-label="Срок" />
    <button
      type="button"
      class="star-btn"
      :class="{ on: important }"
      :aria-pressed="important"
      aria-label="Важная"
      @click="important = !important"
    >
      <Icon name="star" :size="16" />
    </button>
    <button class="btn btn-primary" aria-label="Добавить"><Icon name="plus" :size="16" /> Добавить</button>
  </form>

  <div v-if="!tasks.length" class="empty">
    <strong>Задач нет</strong>
    Добавьте первую в строке выше.
  </div>
  <div v-else class="groups">
    <section v-for="g in groups" :key="g.name" class="group">
      <h2 class="t-label group-title" :class="{ danger: g.name === 'Просрочено' }">
        {{ g.name }} <span class="cnt">{{ g.items.length }}</span>
      </h2>
      <div class="list">
        <div v-for="t in g.items" :key="t.id" class="task" :class="{ done: t.done }">
          <button class="checkbox" :class="{ 'is-checked': t.done }" :aria-label="t.done ? 'Вернуть' : 'Выполнить'" @click="toggle(t)">
            <Icon v-if="t.done" name="check" :size="13" />
          </button>
          <div class="body">
            <div class="ttl">{{ t.title }}</div>
            <div v-if="t.subject_name" class="subj">{{ t.subject_name }}</div>
          </div>
          <button
            class="star-btn sm"
            :class="{ on: t.priority }"
            :aria-pressed="!!t.priority"
            aria-label="Важная"
            @click="togglePrio(t)"
          >
            <Icon name="star" :size="15" />
          </button>
          <div v-if="t.due_date" class="badge mono" :class="overdue(t) ? 'badge-danger' : 'badge-muted'">
            {{ dm(t.due_date) }}
          </div>
          <button class="icon-btn sm danger" aria-label="Удалить" @click="del(t)"><Icon name="trash" :size="15" /></button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.sub {
  margin-top: var(--space-1);
  font-size: var(--text-sm);
}
.chk {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
}
.chk input {
  width: 16px;
  height: 16px;
}
.addbar {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-2);
  margin-bottom: var(--space-6);
  align-items: center;
}
.addbar input,
.addbar .sel {
  border-color: transparent;
  background: var(--color-sunken);
}
.addin {
  flex: 1;
}
.sel {
  max-width: 180px;
}
.due {
  max-width: 150px;
}
.star-btn {
  display: inline-grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: color var(--dur-fast) var(--ease-standard),
    border-color var(--dur-fast) var(--ease-standard);
}
.star-btn.on {
  color: var(--color-accent);
  border-color: var(--color-accent);
}
.star-btn.sm {
  width: 30px;
  height: 30px;
}
.groups {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}
.group-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  color: var(--color-text-secondary);
}
.group-title.danger {
  color: var(--color-danger);
}
.group-title .cnt {
  color: var(--color-text-tertiary);
  font-weight: var(--weight-regular);
}
.list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.task {
  display: grid;
  grid-template-columns: auto 1fr auto auto auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color var(--dur-fast) var(--ease-standard);
}
.task:hover {
  border-color: var(--color-border-strong);
}
.body {
  min-width: 0;
}
.ttl {
  font-size: var(--text-base);
  overflow-wrap: anywhere;
}
.subj {
  margin-top: 2px;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}
.task.done .ttl {
  color: var(--color-text-tertiary);
  text-decoration: line-through;
}

@media (max-width: 759px) {
  .addbar {
    flex-wrap: wrap;
  }
  .addin {
    flex: 1 1 100%;
  }
  .sel,
  .due {
    max-width: none;
    flex: 1;
  }
  .page-head {
    align-items: flex-start;
  }
}
</style>
