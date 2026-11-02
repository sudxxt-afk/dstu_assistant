<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { login } from "../api";

const router = useRouter();
const password = ref("");
const err = ref("");
const busy = ref(false);

async function submit() {
  err.value = "";
  busy.value = true;
  try {
    await login(password.value);
    router.push("/schedule");
  } catch (e) {
    err.value = e.status === 401 ? "Неверный пароль" : "Нет связи с API";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="gate">
    <div class="box">
      <div class="brand">dstu<span class="dim">/assistant</span></div>
      <p class="muted sub">Вход в панель.</p>
      <form @submit.prevent="submit">
        <div class="field">
          <label>Пароль</label>
          <input v-model="password" type="password" placeholder="••••••" autofocus />
        </div>
        <div v-if="err" class="err">{{ err }}</div>
        <button class="btn btn-primary wide" :disabled="busy">
          {{ busy ? "Проверяю…" : "Войти" }}
        </button>
      </form>
      <p class="hint dim">Вход запомнится на этом устройстве.</p>
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
  max-width: 320px;
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
.hint {
  margin-top: 16px;
  font-size: 12px;
  text-align: center;
}
</style>
