<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";
import { HttpRepository } from "@/repositories/HttpRepository";

import vulniverseLogo from "@/assets/vulniverse-logo.png";

const auth = useAuthStore();
const router = useRouter();

const repository = new HttpRepository("/api/v1");
const panelFlags = ref<Record<string, boolean>>({});

watch(
  () => auth.isAuthenticated,
  async (isAuthenticated) => {
    if (!isAuthenticated) return;

    try {
      panelFlags.value = (await repository.getCapabilities()).panels;
    } catch {
      // Leave panelFlags empty — the link just falls back to "shown".
    }
  },
  { immediate: true },
);

// A panel id absent from config defaults to enabled — same convention
// as editor/enabled-extensions.ts's filterEnabled().
const showCnaCredentialsLink = computed(() =>
  (panelFlags.value.vl ?? true) || (panelFlags.value["cve-program"] ?? true),
);

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
      <RouterLink
        v-if="auth.currentUser?.isAdmin"
        to="/admin/users"
        class="text-decoration-none"
      >
        Admin
      </RouterLink>

      <RouterLink
        v-if="showCnaCredentialsLink"
        to="/cna-credentials"
        class="text-decoration-none"
      >
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
