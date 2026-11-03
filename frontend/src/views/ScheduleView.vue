<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { api } from "../api";
import Icon from "../components/Icon.vue";

const nowTick = ref(new Date()); // обновляется раз в 30 с — двигает шкалу текущей пары
let timer;
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
  const now = nowTick.value.toTimeString().slice(0, 5);
  return l.start_time <= now && now <= l.end_time;
}
const TYPE_CLS = { лекция: "is-lecture", практика: "is-practice", лаба: "is-lab", семинар: "is-seminar" };
const typeCls = (t) => TYPE_CLS[t] || "";

/* полоса дней выбранной недели (Пн–Сб) */
const strip = computed(() => {
  const d = new Date(sel.value);
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return Array.from({ length: 6 }, (_, i) => {
    const x = new Date(d);
    x.setDate(d.getDate() + i);
    return { iso: iso(x), wd: SHORT[x.getDay()], n: x.getDate(), date: x };
  });
});
function pick(d) {
  sel.value = d.date;
  mode.value = "day";
  load();
}
const mins = (t) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5));
function progress(l) {
  const n = nowTick.value;
  const cur = n.getHours() * 60 + n.getMinutes() + n.getSeconds() / 60;
  const span = mins(l.end_time) - mins(l.start_time);
  return Math.max(0, Math.min(100, ((cur - mins(l.start_time)) / span) * 100));
}
const statusLabel = (s) => (s === "moved" ? "перенос" : s === "added" ? "доб." : "");

onMounted(() => {
  load();
  timer = setInterval(() => (nowTick.value = new Date()), 30000);
});
onUnmounted(() => clearInterval(timer));
</script>

<template>
  <div class="page-head">
    <div class="segmented">
      <button :class="{ 'is-active': mode === 'day' }" @click="setMode('day')">День</button>
      <button :class="{ 'is-active': mode === 'week' }" @click="setMode('week')">Неделя</button>
    </div>
    <div class="nav">
      <button class="btn btn-sm" @click="today">Сегодня</button>
      <button class="icon-btn" aria-label="Назад" @click="shift(-1)"><Icon name="chevronL" :size="18" /></button>
      <button class="icon-btn" aria-label="Вперёд" @click="shift(1)"><Icon name="chevronR" :size="18" /></button>
    </div>
  </div>

  <div v-if="mode === 'day'" class="strip">
    <button
      v-for="d in strip"
      :key="d.iso"
      class="chip"
      :class="{ 'is-active': d.iso === iso(sel), 'is-today': d.iso === iso(new Date()) }"
      @click="pick(d)"
    >
      <span class="t-eyebrow chipwd">{{ d.wd }}</span>
      <span class="chipn mono">{{ d.n }}</span>
    </button>
  </div>

  <!-- ДЕНЬ -->
  <section v-if="mode === 'day' && day">
    <div class="daytitle">
      <h1 class="t-display">{{ day.weekday }}<span class="dim">, {{ dm(day.date) }}</span></h1>
      <div class="wk">
        <span class="badge">неделя {{ day.week_number }}</span>
        <span class="badge badge-muted">{{ day.parity === "odd" ? "нечётная" : "чётная" }}</span>
        <span v-if="day.lessons.length" class="muted cnt">{{ day.lessons.length }} пар</span>
      </div>
    </div>

    <div v-if="!day.lessons.length" class="empty">
      <strong>Пар нет</strong>
      Свободный день — можно заняться задачами.
    </div>
    <div v-else class="list">
      <article v-for="l in day.lessons" :key="l.pair_number" class="pair" :class="{ now: isNow(l) }">
        <div class="time">
          <div class="mono t1">{{ l.start_time || "—" }}</div>
          <div class="mono t2">{{ l.end_time }}</div>
        </div>
        <div class="body">
          <div v-if="isNow(l)" class="t-eyebrow nowlbl">Идёт сейчас</div>
          <div class="name">{{ l.subject_name }}</div>
          <div class="meta">
            <span class="type-pill" :class="typeCls(l.type)">{{ l.type }}</span>
            <span v-if="statusLabel(l.status)" class="badge">{{ statusLabel(l.status) }}</span>
            <span v-if="l.teacher" class="teacher">{{ l.teacher }}</span>
          </div>
          <div v-if="isNow(l)" class="bar"><i :style="{ width: progress(l) + '%' }"></i></div>
        </div>
        <div class="side">
          <div v-if="l.room" class="room mono">{{ l.room }}</div>
          <div class="num mono">№{{ l.pair_number }}</div>
        </div>
      </article>
    </div>
  </section>

  <!-- НЕДЕЛЯ -->
  <section v-else-if="mode === 'week'" class="weekwrap">
    <div
      v-for="d in week"
      :key="d.date"
      class="col"
      :class="{ today: d.date === iso(new Date()) }"
    >
      <div class="colhead">
        <span class="wd">{{ shortWd(d.date) }}</span>
        <span class="mono dim">{{ dm(d.date) }}</span>
      </div>
      <div v-if="!d.lessons.length" class="cempty dim">Пар нет</div>
      <div v-for="l in d.lessons" :key="l.pair_number" class="cell" :class="typeCls(l.type)">
        <div class="mono ctime">{{ l.start_time }}</div>
        <div class="cname">{{ l.subject_name }}</div>
        <div v-if="l.room" class="mono dim croom">{{ l.room }}</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.nav {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.strip {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-8);
  overflow-x: auto;
  padding-bottom: var(--space-1);
  scrollbar-width: none;
}
.strip .chip {
  flex: 1;
}
.chipn {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
}
.chip.is-active .t-eyebrow {
  color: inherit;
  opacity: 0.8;
}

.daytitle {
  margin-bottom: var(--space-6);
}
.wk {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
}
.cnt {
  font-size: var(--text-sm);
  margin-left: var(--space-1);
}

.list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.pair {
  display: grid;
  grid-template-columns: 64px 1fr auto;
  gap: var(--space-5);
  align-items: center;
  padding: var(--space-4) var(--space-5);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: border-color var(--dur-fast) var(--ease-standard);
}
.pair:hover {
  border-color: var(--color-border-strong);
}
.pair.now {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 1px var(--color-accent);
}
.pair.now .t1 {
  color: var(--color-accent);
}
.t1 {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  line-height: var(--leading-snug);
}
.t2 {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}
.body {
  min-width: 0;
}
.nowlbl {
  color: var(--color-accent);
  margin-bottom: var(--space-1);
}
.name {
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
  line-height: var(--leading-snug);
}
.meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);
}
.teacher {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}
.bar {
  height: 4px;
  margin-top: var(--space-3);
  border-radius: var(--radius-full);
  background: var(--color-sunken);
  overflow: hidden;
}
.bar i {
  display: block;
  height: 100%;
  background: var(--color-accent);
  border-radius: var(--radius-full);
}
.side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-1);
}
.room {
  min-width: 48px;
  text-align: center;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--color-sunken);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
}
.num {
  font-size: var(--text-2xs);
  color: var(--color-text-tertiary);
}

/* неделя */
.weekwrap {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: var(--space-3);
}
.col {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  min-height: 200px;
  background: var(--color-sunken);
  border-radius: var(--radius-lg);
}
.col.today {
  outline: 1px solid var(--color-accent);
  outline-offset: -1px;
}
.colhead {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: var(--space-1) var(--space-1) var(--space-2);
}
.wd {
  font-family: var(--font-display);
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
}
.col.today .wd {
  color: var(--color-accent);
}
.cell {
  --pill: var(--color-text-tertiary);
  padding: var(--space-3);
  background: var(--color-surface);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  border-top: 3px solid var(--pill);
}
.cell.is-lecture { --pill: var(--type-lecture); }
.cell.is-practice { --pill: var(--type-practice); }
.cell.is-lab { --pill: var(--type-lab); }
.cell.is-seminar { --pill: var(--type-seminar); }
.ctime {
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--pill);
}
.cname {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  line-height: var(--leading-snug);
  margin: 2px 0;
  overflow-wrap: anywhere;
}
.croom {
  font-size: var(--text-xs);
}
.cempty {
  padding: var(--space-2) var(--space-1);
  font-size: var(--text-sm);
}

@media (max-width: 759px) {
  .pair {
    grid-template-columns: 52px 1fr auto;
    gap: var(--space-3);
    padding: var(--space-4);
  }
  .weekwrap {
    grid-template-columns: 1fr;
  }
  .col {
    min-height: 0;
  }
}
</style>
