<script setup>
import { ref, computed, onMounted } from "vue";
import { api } from "../api";
import Icon from "../components/Icon.vue";

const mode = ref("day"); // day | week
const sel = ref(new Date());
const day = ref(null);
const week = ref([]);

const SHORT = ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"];
const iso = (d) => d.toISOString().slice(0, 10);
const dm = (s) => s.slice(8, 10) + "." + s.slice(5, 7);
const shortWd = (s) => SHORT[new Date(s).getDay()];

async function load() {
  if (mode.value === "day") {
    day.value = await api.get(`/schedule/day?date=${iso(sel.value)}`);
  } else {
    const all = await api.get(`/schedule/week?date=${iso(sel.value)}`);
    week.value = all.slice(0, 6);
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
    <div class="segmented">
      <button :class="{ 'is-active': mode === 'day' }" @click="setMode('day')">День</button>
      <button :class="{ 'is-active': mode === 'week' }" @click="setMode('week')">Неделя</button>
    </div>
    <div class="nav">
      <button class="btn btn-ghost btn-sm" @click="today">Сегодня</button>
      <button class="icon-btn" @click="shift(-1)"><Icon name="chevronL" :size="18" /></button>
      <button class="icon-btn" @click="shift(1)"><Icon name="chevronR" :size="18" /></button>
    </div>
  </div>

  <!-- ДЕНЬ -->
  <section v-if="mode === 'day' && day">
    <div class="daytitle">
      <h1 class="t-display">{{ day.weekday }}<span class="dim">, {{ dm(day.date) }}</span></h1>
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-6);
}
.nav {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.daytitle {
  margin-bottom: var(--space-5);
}
.wk {
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-accent);
}

.pair {
  display: grid;
  grid-template-columns: 64px 1fr auto;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-3) var(--space-3) 13px;
  border-left: 2px solid transparent;
  border-bottom: 1px solid var(--color-border);
}
.pair.now {
  border-left-color: var(--color-accent);
  background: var(--color-accent-soft);
}
.time {
  font-size: var(--text-sm);
  line-height: var(--leading-snug);
}
.body {
  min-width: 0;
}
.name {
  font-size: var(--text-md);
  font-weight: var(--weight-medium);
}
.num {
  color: var(--color-text-tertiary);
  margin-right: var(--space-2);
  font-size: var(--text-sm);
}
.meta {
  margin-top: var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}
.room {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  align-self: center;
}

/* неделя */
.weekwrap {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 1px;
  background: var(--color-border);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.col {
  background: var(--color-canvas);
  padding: var(--space-3);
  min-height: 160px;
}
.colhead {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-bottom: var(--space-3);
  margin-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}
.wd {
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
}
.cell {
  margin-bottom: var(--space-3);
}
.ctime {
  font-size: var(--text-xs);
  color: var(--color-accent);
}
.cname {
  font-size: var(--text-sm);
  margin: 1px 0;
}
.croom {
  font-size: var(--text-xs);
}
.cempty {
  padding: var(--space-2) 0;
}

@media (max-width: 759px) {
  .head {
    flex-wrap: wrap;
  }
  .weekwrap {
    grid-template-columns: 1fr;
  }
  .col {
    min-height: 0;
  }
}
</style>
