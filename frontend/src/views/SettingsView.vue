<script setup>
import { ref, onMounted } from "vue";
import { api } from "../api";
import Icon from "../components/Icon.vue";

const cfg = ref(null);
const bells = ref([]);
const savedCfg = ref(false);
const savedBells = ref(false);

async function load() {
  cfg.value = await api.get("/config");
  bells.value = await api.get("/bells");
}
async function saveConfig() {
  await api.put("/config", {
    semester_start: cfg.value.semester_start,
    semester_end: cfg.value.semester_end,
    week1_is_odd: cfg.value.week1_is_odd,
    reminder_minutes: Number(cfg.value.reminder_minutes),
    morning_brief_time: cfg.value.morning_brief_time,
  });
  flash(savedCfg);
}
async function saveBells() {
  const body = bells.value
    .filter((b) => b.start_time && b.end_time)
    .map((b) => ({
      pair_number: Number(b.pair_number),
      start_time: b.start_time,
      end_time: b.end_time,
    }));
  await api.put("/bells", body);
  flash(savedBells);
  load();
}
function addBell() {
  const n = bells.value.length + 1;
  bells.value.push({ pair_number: n, start_time: "", end_time: "" });
}
function rmBell(i) {
  bells.value.splice(i, 1);
}
function flash(r) {
  r.value = true;
  setTimeout(() => (r.value = false), 1500);
}
onMounted(load);
</script>

<template>
  <h1>Настройки</h1>

  <div v-if="cfg" class="card block">
    <h2>Семестр</h2>
    <div class="grid">
      <div class="field">
        <label>Начало семестра</label>
        <input type="date" v-model="cfg.semester_start" class="mono" />
      </div>
      <div class="field">
        <label>Конец семестра</label>
        <input type="date" v-model="cfg.semester_end" class="mono" />
      </div>
      <div class="field">
        <label>Первая неделя</label>
        <select v-model="cfg.week1_is_odd">
          <option :value="true">нечётная</option>
          <option :value="false">чётная</option>
        </select>
      </div>
      <div class="field">
        <label>Напоминание, мин</label>
        <input type="number" v-model="cfg.reminder_minutes" class="mono" />
      </div>
      <div class="field">
        <label>Утренний бриф</label>
        <input type="time" v-model="cfg.morning_brief_time" class="mono" />
      </div>
    </div>
    <div class="row savebar">
      <button class="btn btn-primary btn-sm" @click="saveConfig">Сохранить</button>
      <span v-if="savedCfg" class="ok">сохранено</span>
    </div>
  </div>

  <div class="card block">
    <div class="spread row">
      <h2>Звонки</h2>
      <button class="btn btn-ghost btn-sm" @click="addBell"><Icon name="plus" :size="14" /> пара</button>
    </div>
    <div class="bells">
      <div v-for="(b, i) in bells" :key="i" class="bell">
        <span class="num mono">{{ b.pair_number }}</span>
        <input type="time" v-model="b.start_time" class="mono" />
        <span class="dim">—</span>
        <input type="time" v-model="b.end_time" class="mono" />
        <button class="mini del" @click="rmBell(i)"><Icon name="trash" :size="14" /></button>
      </div>
    </div>
    <div class="row savebar">
      <button class="btn btn-primary btn-sm" @click="saveBells">Сохранить</button>
      <span v-if="savedBells" class="ok">сохранено</span>
    </div>
  </div>
</template>

<style scoped>
h1 {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.02em;
  margin-bottom: 20px;
}
h2 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 14px;
}
.block {
  padding: 18px;
  margin-bottom: 18px;
  max-width: 560px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}
.savebar {
  margin-top: 16px;
  gap: 12px;
}
.ok {
  font-size: 12px;
  color: var(--accent);
}
.bells {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.bell {
  display: grid;
  grid-template-columns: 20px 1fr auto 1fr auto;
  align-items: center;
  gap: 10px;
}
.bell input {
  max-width: 130px;
}
.num {
  color: var(--fg-3);
  font-size: 13px;
}
.mini {
  display: flex;
  padding: 4px;
  color: var(--fg-3);
}
.mini.del:hover {
  color: var(--danger);
}
@media (max-width: 759px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
