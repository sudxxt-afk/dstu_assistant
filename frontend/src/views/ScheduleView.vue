<script setup>
import { ref, computed, onMounted } from "vue";
import { api } from "../api";
import Icon from "../components/Icon.vue";

const mode = ref("day"); // day | week
const sel = ref(new Date());
const day = ref(null);
const week = ref([]);
const loading = ref(false);

const SHORT = ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"];
const iso = (d) => d.toISOString().slice(0, 10);
const dm = (s) => s.slice(8, 10) + "." + s.slice(5, 7);
const shortWd = (s) => SHORT[new Date(s).getDay()];

async function load() {
  loading.value = true;
  try {
    if (mode.value === "day") {
      day.value = await api.get(`/schedule/day?date=${iso(sel.value)}`);
    } else {
      const all = await api.get(`/schedule/week?date=${iso(sel.value)}`);
      week.value = all.slice(0, 6); // Пн–Сб
    }
  } finally {
    loading.value = false;
  }
}

function shift(n) {
  const d = new Date(sel.value);
  d.setDate(d.getDate() + (mode.value === "week" ? n * 7 : n));
  sel.value = d;
  load();
}
function today() {
  sel.value = new Date();
  load();
}
function setMode(m) {
  mode.value = m;
  load();
}

const isToday = computed(() => iso(sel.value) === iso(new Date()));
function isNow(l) {
  if (!isToday.value || !l.start_time) return false;
  const now = new Date().toTimeString().slice(0, 5);
  return l.start_time <= now && now <= l.end_time;
}
const statusLabel = (s) => (s === "moved" ? "перенос" : s === "added" ? "доб." : "");

onMounted(load);
</script>

<template>
  <div class="head spread">
    <div class="toggle">
      <button :class="{ on: mode === 'day' }" @click="setMode('day')">День</button>
      <button :class="{ on: mode === 'week' }" @click="setMode('week')">Неделя</button>
    </div>
    <div class="nav">
      <button class="btn btn-ghost btn-sm" @click="today">Сегодня</button>
      <button class="ico" @click="shift(-1)"><Icon name="chevronL" :size="18" /></button>
      <button class="ico" @click="shift(1)"><Icon name="chevronR" :size="18" /></button>
    </div>
  </div>

  <!-- ДЕНЬ -->
  <section v-if="mode === 'day' && day">
    <div class="daytitle">
      <h1>{{ day.weekday }}<span class="dim">, {{ dm(day.date) }}</span></h1>
      <div class="mono wk">неделя {{ day.week_number }} · {{ day.parity === "odd" ? "нечётная" : "чётная" }}</div>
    </div>

    <div v-if="!day.lessons.length" class="empty">Пар нет</div>
    <div v-else class="list">
      <div v-for="l in day.lessons" :key="l.pair_number" class="pair" :class="{ now: isNow(l) }">
        <div class="time mono">
          <div>{{ l.start_time || "—" }}</div>
          <div class="dim">{{ l.end_time }}</div>
        </div>
        <div class="body">
          <div class="name">
            <span class="num mono">{{ l.pair_number }}</span>{{ l.subject_name }}
            <span v-if="statusLabel(l.status)" class="badge">{{ statusLabel(l.status) }}</span>
          </div>
          <div class="meta">
            <span class="tag">{{ l.type }}</span>
            <template v-if="l.teacher"> · {{ l.teacher }}</template>
          </div>
        </div>
        <div class="room mono">{{ l.room }}</div>
      </div>
    </div>
  </section>

  <!-- НЕДЕЛЯ -->
  <section v-else-if="mode === 'week'" class="weekwrap">
    <div v-for="d in week" :key="d.date" class="col">
      <div class="colhead">
        <span class="wd">{{ shortWd(d.date) }}</span>
        <span class="mono dim">{{ dm(d.date) }}</span>
      </div>
      <div v-if="!d.lessons.length" class="cempty dim">—</div>
      <div v-for="l in d.lessons" :key="l.pair_number" class="cell">
        <div class="mono ctime">{{ l.start_time }}</div>
        <div class="cname">{{ l.subject_name }}</div>
        <div class="mono dim croom">{{ l.room }}</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.head {
  margin-bottom: 22px;
}
.toggle {
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.toggle button {
  padding: 7px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--fg-2);
}
.toggle button.on {
  background: var(--surface);
  color: var(--fg);
}
.nav {
  display: flex;
  align-items: center;
  gap: 6px;
}
.ico {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  color: var(--fg-2);
}
.ico:hover {
  background: var(--surface);
  color: var(--fg);
}

.daytitle {
  margin-bottom: 18px;
}
h1 {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.02em;
}
.wk {
  margin-top: 4px;
  font-size: 12px;
  color: var(--accent);
}

.list {
  display: flex;
  flex-direction: column;
}
.pair {
  display: grid;
  grid-template-columns: 64px 1fr auto;
  gap: 16px;
  padding: 14px 14px 14px 13px;
  border-left: 2px solid transparent;
  border-bottom: 1px solid var(--line);
}
.pair.now {
  border-left-color: var(--accent);
  background: var(--accent-soft);
}
.time {
  font-size: 13px;
  line-height: 1.4;
}
.body {
  min-width: 0;
}
.name {
  font-size: 15px;
  font-weight: 500;
}
.num {
  color: var(--fg-3);
  margin-right: 8px;
  font-size: 13px;
}
.badge {
  margin-left: 8px;
  font-size: 11px;
  color: var(--accent);
  border: 1px solid var(--accent-line);
  border-radius: 3px;
  padding: 1px 5px;
}
.meta {
  margin-top: 3px;
  font-size: 13px;
  color: var(--fg-2);
}
.room {
  font-size: 13px;
  color: var(--fg-2);
  align-self: center;
}
.empty {
  color: var(--fg-3);
  padding: 20px 0;
}

/* неделя */
.weekwrap {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}
.col {
  background: var(--bg);
  padding: 10px;
  min-height: 160px;
}
.colhead {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-bottom: 10px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--line);
}
.wd {
  font-size: 12px;
  font-weight: 600;
}
.cell {
  margin-bottom: 12px;
}
.ctime {
  font-size: 12px;
  color: var(--accent);
}
.cname {
  font-size: 13px;
  margin: 1px 0;
}
.croom {
  font-size: 12px;
}
.cempty {
  padding: 8px 0;
}
@media (max-width: 759px) {
  .weekwrap {
    grid-template-columns: 1fr;
  }
  .col {
    min-height: 0;
  }
}
</style>
