<script setup>
import { useRoute } from "vue-router";
import AppShell from "./components/AppShell.vue";
const route = useRoute();
</script>

<template>
  <AppShell v-if="route.path !== '/login'"><router-view /></AppShell>
  <router-view v-else />
</template>
