<script setup>
import { ref, computed, onMounted } from "vue";
import { api } from "../api";
import Icon from "../components/Icon.vue";

const subjects = ref([]);
const lessons = ref([]);

const WD = ["", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"];
const TYPES = ["лекция", "практика", "лаба", "семинар"];
const PARITY = [
  { v: "every", t: "каждую" },
  { v: "odd", t: "нечётная" },
  { v: "even", t: "чётная" },
];
const parityLabel = (v) => PARITY.find((p) => p.v === v)?.t || v;
const subjName = (id) => subjects.value.find((s) => s.id === id)?.name || "?";

async function load() {
  subjects.value = await api.get("/subjects");
  lessons.value = await api.get("/lessons");
}

const byDay = computed(() => {
  const g = {};
  for (let d = 1; d <= 6; d++) g[d] = [];
  for (const l of lessons.value) if (g[l.weekday]) g[l.weekday].push(l);
  for (const d in g) g[d].sort((a, b) => a.pair_number - b.pair_number);
  return g;
});

/* --- предметы --- */
const subjForm = ref({ id: null, name: "", teacher: "" });
async function saveSubject() {
  if (!subjForm.value.name.trim()) return;
  const body = { name: subjForm.value.name.trim(), teacher: subjForm.value.teacher.trim() || null };
  if (subjForm.value.id) await api.patch(`/subjects/${subjForm.value.id}`, body);
  else await api.post("/subjects", body);
  subjForm.value = { id: null, name: "", teacher: "" };
  await load();
}
function editSubject(s) {
  subjForm.value = { id: s.id, name: s.name, teacher: s.teacher || "" };
}
async function delSubject(s) {
  if (!confirm(`Удалить предмет «${s.name}»?`)) return;
  await api.del(`/subjects/${s.id}`);
  await load();
}

/* --- пары --- */
const blankLesson = () => ({
  id: null, subject_id: subjects.value[0]?.id ?? null, type: "лекция",
  weekday: 1, pair_number: 1, parity: "every", room: "", teacher_override: "",
});
const lf = ref(null);
function newLesson() {
  lf.value = blankLesson();
}
function editLesson(l) {
  lf.value = { ...l, teacher_override: l.teacher_override || "", room: l.room || "" };
}
async function saveLesson() {
  const b = {
    subject_id: lf.value.subject_id, type: lf.value.type,
    weekday: Number(lf.value.weekday), pair_number: Number(lf.value.pair_number),
    room: lf.value.room.trim() || null, parity: lf.value.parity,
    teacher_override: lf.value.teacher_override.trim() || null,
  };
  if (lf.value.id) await api.patch(`/lessons/${lf.value.id}`, b);
  else await api.post("/lessons", b);
  lf.value = null;
  await load();
}
async function delLesson(l) {
  await api.del(`/lessons/${l.id}`);
  await load();
}

onMounted(load);
</script>

<template>
  <h1>Редактор</h1>

  <!-- ПАРЫ -->
  <div class="sec spread">
    <h2>Пары</h2>
    <button class="btn btn-primary btn-sm" @click="newLesson" :disabled="!subjects.length">
      <Icon name="plus" :size="15" /> Пара
    </button>
  </div>

  <div v-if="lf" class="form card">
    <div class="formtitle">{{ lf.id ? "Изменить пару" : "Новая пара" }}</div>
    <div class="grid">
      <div class="field col2">
        <label>Предмет</label>
        <select v-model="lf.subject_id">
          <option v-for="s in subjects" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>
      <div class="field">
        <label>Тип</label>
        <select v-model="lf.type"><option v-for="t in TYPES" :key="t">{{ t }}</option></select>
      </div>
      <div class="field">
        <label>Неделя</label>
        <select v-model="lf.parity">
          <option v-for="p in PARITY" :key="p.v" :value="p.v">{{ p.t }}</option>
        </select>
      </div>
      <div class="field">
        <label>День</label>
        <select v-model="lf.weekday">
          <option v-for="d in 6" :key="d" :value="d">{{ WD[d] }}</option>
        </select>
      </div>
      <div class="field">
        <label>Пара</label>
        <select v-model="lf.pair_number">
          <option v-for="n in 8" :key="n" :value="n">{{ n }}</option>
        </select>
      </div>
      <div class="field">
        <label>Аудитория</label>
        <input v-model="lf.room" placeholder="542" />
      </div>
      <div class="field col2">
        <label>Препод <span class="dim">(если отличается от предмета)</span></label>
        <input v-model="lf.teacher_override" placeholder="из предмета" />
      </div>
    </div>
    <div class="row spread actions">
      <button class="btn btn-ghost btn-sm" @click="lf = null">Отмена</button>
      <button class="btn btn-primary btn-sm" @click="saveLesson">Сохранить</button>
    </div>
  </div>

  <div class="days">
    <div v-for="d in 6" :key="d" class="day">
      <div class="dayhead">{{ WD[d] }}</div>
      <div v-if="!byDay[d].length" class="dim small">—</div>
      <div v-for="l in byDay[d]" :key="l.id" class="lrow">
        <span class="num mono">{{ l.pair_number }}</span>
        <div class="linfo">
          <div class="lname">{{ subjName(l.subject_id) }}</div>
          <div class="lmeta">
            <span class="tag">{{ l.type }}</span>
            <span v-if="l.parity !== 'every'" class="pbadge">{{ parityLabel(l.parity) }}</span>
            <span v-if="l.room" class="mono dim"> · {{ l.room }}</span>
          </div>
        </div>
        <button class="mini" @click="editLesson(l)"><Icon name="editor" :size="14" /></button>
        <button class="mini del" @click="delLesson(l)"><Icon name="trash" :size="14" /></button>
      </div>
    </div>
  </div>

  <!-- ПРЕДМЕТЫ -->
  <div class="sec"><h2>Предметы</h2></div>
  <form class="subjbar" @submit.prevent="saveSubject">
    <input v-model="subjForm.name" placeholder="Название" />
    <input v-model="subjForm.teacher" placeholder="Преподаватель" />
    <button class="btn btn-primary btn-sm">{{ subjForm.id ? "Сохранить" : "Добавить" }}</button>
    <button v-if="subjForm.id" type="button" class="btn btn-ghost btn-sm" @click="subjForm = { id: null, name: '', teacher: '' }">×</button>
  </form>
  <div class="subjlist">
    <div v-for="s in subjects" :key="s.id" class="srow">
      <div class="sname">{{ s.name }}</div>
      <div class="muted small">{{ s.teacher }}</div>
      <button class="mini" @click="editSubject(s)"><Icon name="editor" :size="14" /></button>
      <button class="mini del" @click="delSubject(s)"><Icon name="trash" :size="14" /></button>
    </div>
  </div>
</template>

<style scoped>
h1 {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.02em;
}
h2 {
  font-size: 15px;
  font-weight: 600;
}
.sec {
  margin: 28px 0 14px;
}
.form {
  padding: 16px;
  margin-bottom: 18px;
}
.formtitle {
  font-size: 13px;
  font-weight: 600;
  color: var(--fg-2);
  margin-bottom: 14px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.col2 {
  grid-column: span 2;
}
.actions {
  margin-top: 16px;
}

.days {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}
.day {
  background: var(--bg);
  padding: 12px 14px;
}
.dayhead {
  font-size: 12px;
  font-weight: 600;
  color: var(--fg-2);
  margin-bottom: 10px;
}
.lrow {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: 10px;
  padding: 7px 0;
}
.num {
  color: var(--fg-3);
  font-size: 13px;
  width: 14px;
}
.lname {
  font-size: 14px;
}
.lmeta {
  font-size: 12px;
  color: var(--fg-2);
  margin-top: 1px;
}
.pbadge {
  color: var(--accent);
  font-size: 11px;
  margin-left: 4px;
}
.mini {
  display: flex;
  padding: 4px;
  color: var(--fg-3);
  border-radius: 3px;
}
.mini:hover {
  color: var(--fg);
  background: var(--surface-2);
}
.mini.del:hover {
  color: var(--danger);
}

.subjbar {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}
.subjlist {
  display: flex;
  flex-direction: column;
}
.srow {
  display: grid;
  grid-template-columns: 1fr 1fr auto auto;
  align-items: center;
  gap: 10px;
  padding: 10px 2px;
  border-bottom: 1px solid var(--line);
}
.sname {
  font-size: 14px;
}
.small {
  font-size: 12px;
}

@media (max-width: 759px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .col2 {
    grid-column: span 2;
  }
  .days {
    grid-template-columns: 1fr;
  }
}
</style>
