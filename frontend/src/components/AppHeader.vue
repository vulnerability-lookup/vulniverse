<script setup lang="ts">
import { useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";

import vulniverseLogo from "@/assets/vulniverse-logo.png";

const auth = useAuthStore();
const router = useRouter();

async function onLogout(): Promise<void> {
  await auth.logout();
  await router.replace("/login");
}
</script>

<template>
  <header class="navbar navbar-expand bg-body-tertiary border-bottom px-3">
    <RouterLink to="/" class="navbar-brand">
      <img :src="vulniverseLogo" alt="Vulniverse" class="app-header-logo">
    </RouterLink>

    <nav
      v-if="auth.isAuthenticated"
      class="d-flex align-items-center ms-auto gap-3"
    >
      <RouterLink to="/cna-credentials" class="text-decoration-none">
        CNA credentials
      </RouterLink>

      <span class="text-secondary">{{ auth.currentUser?.email }}</span>

      <button
        type="button"
        class="btn btn-outline-secondary btn-sm"
        @click="onLogout"
      >
        Log out
      </button>
    </nav>
  </header>
</template>

<style scoped>
.app-header-logo {
  display: block;
  height: 1.75rem;
  width: auto;
}
</style>
