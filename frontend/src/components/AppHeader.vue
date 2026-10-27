<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";
import { HttpRepository } from "@/repositories/HttpRepository";

import vulniverseLogo from "@/assets/vulniverse-icon.png";

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

// A panel id absent from config defaults to enabled.
const showCnaCredentialsLink = computed(() =>
  (panelFlags.value.vl ?? true) ||
  (panelFlags.value["cve-program"] ?? true),
);

async function onLogout(): Promise<void> {
  await auth.logout();
  await router.replace("/login");
}
</script>

<template>
  <header class="navbar navbar-expand bg-body-tertiary border-bottom px-3">
    <RouterLink
      :to="auth.isLocalMode ? '/records' : '/'"
      class="navbar-brand"
    >
      <img
        :src="vulniverseLogo"
        alt="Vulniverse"
        class="app-header-logo"
      >
    </RouterLink>

    <!-- Authenticated navigation (local and multi-user) -->
    <nav
      v-if="auth.isAuthenticated"
      class="d-flex align-items-center ms-auto gap-3"
    >
      <RouterLink
        to="/records"
        class="text-decoration-none"
      >
        Records
      </RouterLink>

      <RouterLink
        v-if="!auth.isLocalMode && auth.currentUser?.isAdmin"
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

      <!-- Local mode -->
      <template v-if="auth.isLocalMode">
        <span class="text-secondary">
          Local workspace
        </span>
      </template>

      <!-- Multi-user mode -->
      <template v-else>
        <span class="text-secondary">
          {{ auth.currentUser?.email }}
        </span>

        <button
          type="button"
          class="btn btn-outline-secondary btn-sm"
          @click="onLogout"
        >
          Log out
        </button>
      </template>
    </nav>

    <!-- Anonymous navigation (multi-user mode) -->
    <nav
      v-else
      class="d-flex align-items-center ms-auto gap-3"
    >
      <RouterLink
        to="/try"
        class="text-decoration-none"
      >
        Try it
      </RouterLink>

      <RouterLink
        to="/login"
        class="text-decoration-none"
      >
        Log in
      </RouterLink>

      <RouterLink
        to="/register"
        class="btn btn-primary btn-sm"
      >
        Register
      </RouterLink>
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
