<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { api, setToken, setBase } from "../api";

const router = useRouter();
const token = ref("");
const base = ref(localStorage.getItem("api_base") || "");
const err = ref("");
const busy = ref(false);

async function submit() {
  err.value = "";
  busy.value = true;
  setBase(base.value.trim());
  setToken(token.value.trim());
  try {
    await api.get("/subjects");
    router.push("/schedule");
  } catch (e) {
    err.value =
      e.status === 401 ? "Неверный токен" : "Нет связи с API: " + (e.message || "");
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="gate">
    <div class="box">
      <div class="brand">dstu<span class="dim">/assistant</span></div>
      <p class="muted sub">Вставь API-токен, чтобы подключить панель к боту.</p>
      <form @submit.prevent="submit">
        <div class="field">
          <label>API-токен</label>
          <input v-model="token" class="mono" type="password" placeholder="X-API-Token" autofocus />
        </div>
        <div class="field">
          <label>Адрес API <span class="dim">(необязательно)</span></label>
          <input v-model="base" class="mono" placeholder="http://192.168.0.174:8000/api" />
        </div>
        <div v-if="err" class="err">{{ err }}</div>
        <button class="btn btn-primary wide" :disabled="busy">
          {{ busy ? "Проверяю…" : "Войти" }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.gate {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 20px;
}
.box {
  width: 100%;
  max-width: 360px;
}
.brand {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.sub {
  margin: 8px 0 24px;
  font-size: 13px;
}
form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.wide {
  width: 100%;
  justify-content: center;
  height: 38px;
  margin-top: 4px;
}
.err {
  color: var(--danger);
  font-size: 13px;
}
</style>
