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
  padding: var(--space-5);
}
.box {
  width: 100%;
  max-width: 320px;
}
.brand {
  font-size: var(--text-xl);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-tight);
}
.sub {
  margin: var(--space-2) 0 var(--space-6);
  font-size: var(--text-sm);
}
form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.wide {
  width: 100%;
  height: 38px;
  margin-top: var(--space-1);
}
.err {
  color: var(--color-danger);
  font-size: var(--text-sm);
}
.hint {
  margin-top: var(--space-4);
  font-size: var(--text-xs);
  text-align: center;
}
</style>
