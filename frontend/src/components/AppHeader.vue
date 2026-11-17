<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";
import { HttpRepository } from "@/repositories/HttpRepository";

import vulniverseLogo from "@/assets/vulniverse-icon.png";

import { nextTheme, themePreference } from "@/theme";

const THEME_LABELS = { auto: "System", light: "Light", dark: "Dark" } as const;

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

    <button
      type="button"
      class="btn btn-outline-secondary btn-sm ms-3 d-inline-flex align-items-center gap-1"
      :title="`Theme: ${THEME_LABELS[themePreference]} (click to change)`"
      :aria-label="`Theme: ${THEME_LABELS[themePreference]}. Change theme`"
      @click="nextTheme"
    >
      <svg
        class="app-header-theme-icon"
        viewBox="0 0 16 16"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <!-- System: half-filled circle; light: sun; dark: moon. -->
        <template v-if="themePreference === 'auto'">
          <circle
            cx="8"
            cy="8"
            r="6"
          />
          <path
            d="M8 2a6 6 0 0 0 0 12Z"
            fill="currentColor"
          />
        </template>
        <template v-else-if="themePreference === 'light'">
          <circle
            cx="8"
            cy="8"
            r="3"
          />
          <path d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M3 3l1 1M12 12l1 1M3 13l1-1M12 4l1-1" />
        </template>
        <path
          v-else
          d="M13.5 9.5A6 6 0 0 1 6.5 2.5a6 6 0 1 0 7 7Z"
        />
      </svg>
      {{ THEME_LABELS[themePreference] }}
    </button>
  </header>
</template>

<style scoped>
.app-header-theme-icon {
  width: 1rem;
  height: 1rem;
}

.app-header-logo {
  display: block;
  height: 1.75rem;
  width: auto;
}
</style>
