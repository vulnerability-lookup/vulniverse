<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";
import { HttpRepository } from "@/repositories/HttpRepository";

import vulniverseIcon from "@/assets/vulniverse-icon.png";
import vulniverseLogo from "@/assets/vulniverse-logo-header.webp";
import vulniverseLogoDark from "@/assets/vulniverse-logo-header-dark.webp";

import { appTheme, nextTheme, themePreference } from "@/theme";

import type { ThemePreference } from "@/editor/core/theme";

/*
 * The standalone app's top bar: the main places on the left (with the
 * current one highlighted), the organisation and menus on the right —
 * Admin for instance admins, and the account menu with CNA credentials,
 * the theme and logging out.
 */

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

// 16×16 line icons (stroke paths), like the editor's.
const ICONS = {
  records: "M4 1.5h5.5L13 5v9.5H4ZM9.5 1.5V5H13M6.5 8.5h4M6.5 11h4",
  members: "M6 7.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM1.5 14c0-2.5 2-4 4.5-4s4.5 1.5 4.5 4M11 7a2 2 0 1 0 0-4M12 10c1.5.3 2.5 1.6 2.5 3.5",
  organisation: "M2.5 14.5V3.5l6-2v13M8.5 6l5 1.5v7M1.5 14.5h13M4.5 5.5h2M4.5 8h2M4.5 10.5h2M10.5 9.5h1M10.5 12h1",
  admin: "M8 1.5l5.5 2v4c0 3.5-2.4 6-5.5 7-3.1-1-5.5-3.5-5.5-7v-4L8 1.5ZM8 6v3M8 11v.01",
  account: "M8 7.5a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM2.5 14.5c0-3 2.5-5 5.5-5s5.5 2 5.5 5",
  key: "M10 9.5a3.5 3.5 0 1 0-3.4-2.7L1.5 12v2.5H4V13h1.5v-1.5H7l1.1-1.1A3.5 3.5 0 0 0 10 9.5ZM11 5v.01",
  logout: "M6 14.5H2.5v-13H6M10.5 11 14 8l-3.5-3M14 8H6",
  check: "M3 8.5l3 3 7-7",
  chevron: "M4 6l4 4 4-4",
} as const;

const THEMES: { id: ThemePreference; label: string; icon: string }[] = [
  { id: "auto", label: "System", icon: "M8 2a6 6 0 1 0 0 12ZM8 2a6 6 0 0 1 0 12" },
  { id: "light", label: "Light", icon: "M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M3 3l1 1M12 12l1 1M3 13l1-1M12 4l1-1" },
  { id: "dark", label: "Dark", icon: "M13.5 9.5A6 6 0 0 1 6.5 2.5a6 6 0 1 0 7 7Z" },
];

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

const multiUser = computed(() => auth.isAuthenticated && !auth.isLocalMode);
const isOrganisationAdmin = computed(() => auth.currentOrganisation?.role === "admin");
const accountLabel = computed(() => (
  auth.isLocalMode ? "Local workspace" : auth.currentUser?.email ?? ""
));
const initial = computed(() => accountLabel.value.charAt(0).toUpperCase());

// --- Menus -------------------------------------------------------------------

const openMenu = ref<"admin" | "account" | null>(null);

function toggle(menu: "admin" | "account"): void {
  openMenu.value = openMenu.value === menu ? null : menu;
}

// Focus leaving the menu (Tab away, click elsewhere) closes it.
function closeOnLeave(event: FocusEvent): void {
  if (!(event.currentTarget as HTMLElement).contains(event.relatedTarget as Node | null)) {
    openMenu.value = null;
  }
}

// Following a link in a menu (or anywhere) closes it.
watch(() => route.fullPath, () => {
  openMenu.value = null;
});

function chooseTheme(theme: ThemePreference): void {
  themePreference.value = theme;
}

// --- Organisation ------------------------------------------------------------

const switchError = ref<string | null>(null);

// Switching shows that organisation's records.
async function onSwitchOrganisation(event: Event): Promise<void> {
  switchError.value = null;

  try {
    await auth.switchOrganisation(Number((event.target as HTMLSelectElement).value));
    await router.push({ name: "records" });
  } catch (error) {
    switchError.value = error instanceof Error ? error.message : "Unable to switch.";
  }
}

async function onLogout(): Promise<void> {
  openMenu.value = null;
  await auth.logout();
  await router.replace("/login");
}
</script>

<template>
  <header class="app-header">
    <RouterLink
      :to="auth.isLocalMode ? '/records' : '/'"
      class="app-header-brand"
      aria-label="Vulniverse home"
    >
      <img
        :src="appTheme === 'dark' ? vulniverseLogoDark : vulniverseLogo"
        alt=""
        class="app-header-logo"
      >
      <img
        :src="vulniverseIcon"
        alt=""
        class="app-header-icon"
      >
    </RouterLink>

    <nav
      v-if="auth.isAuthenticated"
      class="app-header-nav"
      aria-label="Main"
    >
      <RouterLink
        to="/records"
        class="app-header-link"
      >
        <svg
          class="app-header-svg"
          viewBox="0 0 16 16"
          aria-hidden="true"
        ><path :d="ICONS.records" /></svg>
        <span>Records</span>
      </RouterLink>

      <RouterLink
        v-if="multiUser && isOrganisationAdmin"
        to="/organisation"
        class="app-header-link"
        title="Members and invitation links of your organisation"
      >
        <svg
          class="app-header-svg"
          viewBox="0 0 16 16"
          aria-hidden="true"
        ><path :d="ICONS.members" /></svg>
        <span>Members</span>
      </RouterLink>
    </nav>

    <div class="app-header-end">
      <!-- The organisation: a switcher with several, a label with one. -->
      <template v-if="multiUser && auth.currentUser">
        <label
          v-if="auth.currentUser.organisations.length > 1"
          class="app-header-organisation"
          :title="switchError ?? 'Current organisation: new records go here'"
        >
          <svg
            class="app-header-svg"
            viewBox="0 0 16 16"
            aria-hidden="true"
          ><path :d="ICONS.organisation" /></svg>
          <span class="visually-hidden">Current organisation</span>
          <select
            class="form-select form-select-sm"
            :value="auth.currentUser.currentOrganisationId"
            @change="onSwitchOrganisation"
          >
            <option
              v-for="organisation in auth.currentUser.organisations"
              :key="organisation.id"
              :value="organisation.id"
            >
              {{ organisation.name }}
            </option>
          </select>
        </label>

        <span
          v-else-if="auth.currentOrganisation"
          class="app-header-organisation"
          title="Your organisation"
        >
          <svg
            class="app-header-svg"
            viewBox="0 0 16 16"
            aria-hidden="true"
          ><path :d="ICONS.organisation" /></svg>
          <span class="app-header-organisation-name">{{ auth.currentOrganisation.name }}</span>
        </span>
      </template>

      <!-- Instance administration. -->
      <div
        v-if="multiUser && auth.currentUser?.isAdmin"
        class="dropdown"
        @focusout="closeOnLeave"
        @keydown.esc="openMenu = null"
      >
        <button
          type="button"
          class="app-header-button"
          aria-haspopup="menu"
          :aria-expanded="openMenu === 'admin'"
          @click="toggle('admin')"
        >
          <svg
            class="app-header-svg"
            viewBox="0 0 16 16"
            aria-hidden="true"
          ><path :d="ICONS.admin" /></svg>
          <span class="app-header-collapsible">Admin</span>
          <svg
            class="app-header-chevron"
            viewBox="0 0 16 16"
            aria-hidden="true"
          ><path :d="ICONS.chevron" /></svg>
        </button>

        <ul
          :class="['dropdown-menu', 'dropdown-menu-end', { show: openMenu === 'admin' }]"
          role="menu"
        >
          <li role="none">
            <RouterLink
              to="/admin/users"
              class="dropdown-item"
              role="menuitem"
            >
              Users
            </RouterLink>
          </li>
          <li role="none">
            <RouterLink
              to="/admin/organisations"
              class="dropdown-item"
              role="menuitem"
            >
              Organisations
            </RouterLink>
          </li>
        </ul>
      </div>

      <!-- The account: who's logged in, credentials, theme, log out. -->
      <div
        v-if="auth.isAuthenticated"
        class="dropdown"
        @focusout="closeOnLeave"
        @keydown.esc="openMenu = null"
      >
        <button
          type="button"
          class="app-header-button"
          aria-haspopup="menu"
          :aria-expanded="openMenu === 'account'"
          :aria-label="`Account menu for ${accountLabel}`"
          @click="toggle('account')"
        >
          <span
            class="app-header-avatar"
            aria-hidden="true"
          >{{ initial }}</span>
          <span class="app-header-collapsible app-header-email">{{ accountLabel }}</span>
          <svg
            class="app-header-chevron"
            viewBox="0 0 16 16"
            aria-hidden="true"
          ><path :d="ICONS.chevron" /></svg>
        </button>

        <ul
          :class="['dropdown-menu', 'dropdown-menu-end', 'app-header-menu', { show: openMenu === 'account' }]"
          role="menu"
        >
          <li
            role="none"
            class="dropdown-header text-truncate"
          >
            {{ auth.isLocalMode ? "Local workspace" : `Signed in as ${accountLabel}` }}
          </li>

          <li
            v-if="!auth.isLocalMode"
            role="none"
          >
            <RouterLink
              to="/account"
              class="dropdown-item"
              role="menuitem"
            >
              <svg
                class="app-header-svg"
                viewBox="0 0 16 16"
                aria-hidden="true"
              ><path :d="ICONS.account" /></svg>
              Account settings
            </RouterLink>
          </li>

          <li
            v-if="showCnaCredentialsLink"
            role="none"
          >
            <RouterLink
              to="/cna-credentials"
              class="dropdown-item"
              role="menuitem"
            >
              <svg
                class="app-header-svg"
                viewBox="0 0 16 16"
                aria-hidden="true"
              ><path :d="ICONS.key" /></svg>
              CNA credentials
            </RouterLink>
          </li>

          <li role="none">
            <hr class="dropdown-divider">
          </li>
          <li
            role="none"
            class="dropdown-header"
          >
            Theme
          </li>
          <li
            v-for="theme in THEMES"
            :key="theme.id"
            role="none"
          >
            <button
              type="button"
              class="dropdown-item"
              role="menuitemradio"
              :aria-checked="themePreference === theme.id"
              @click="chooseTheme(theme.id)"
            >
              <svg
                class="app-header-svg"
                viewBox="0 0 16 16"
                aria-hidden="true"
              ><path :d="theme.icon" /></svg>
              {{ theme.label }}
              <svg
                v-if="themePreference === theme.id"
                class="app-header-svg ms-auto"
                viewBox="0 0 16 16"
                aria-hidden="true"
              ><path :d="ICONS.check" /></svg>
            </button>
          </li>

          <template v-if="!auth.isLocalMode">
            <li role="none">
              <hr class="dropdown-divider">
            </li>
            <li role="none">
              <button
                type="button"
                class="dropdown-item"
                role="menuitem"
                @click="onLogout"
              >
                <svg
                  class="app-header-svg"
                  viewBox="0 0 16 16"
                  aria-hidden="true"
                ><path :d="ICONS.logout" /></svg>
                Log out
              </button>
            </li>
          </template>
        </ul>
      </div>

      <!-- Logged out (multi-user mode). -->
      <template v-else>
        <RouterLink
          to="/try"
          class="app-header-link"
        >
          Try it
        </RouterLink>
        <RouterLink
          to="/login"
          class="app-header-link"
        >
          Log in
        </RouterLink>
        <RouterLink
          to="/register"
          class="btn btn-primary btn-sm"
        >
          Register
        </RouterLink>
        <button
          type="button"
          class="app-header-button"
          :title="`Theme: ${THEMES.find((t) => t.id === themePreference)?.label} (click to change)`"
          :aria-label="`Theme: ${THEMES.find((t) => t.id === themePreference)?.label}. Change theme`"
          @click="nextTheme"
        >
          <svg
            class="app-header-svg"
            viewBox="0 0 16 16"
            aria-hidden="true"
          ><path :d="THEMES.find((t) => t.id === themePreference)?.icon" /></svg>
        </button>
      </template>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  min-height: 3.5rem;
  padding: 0.5rem 1.25rem;
  background: var(--bs-body-bg);
  border-bottom: 1px solid var(--bs-border-color);
}

.app-header-brand {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
}

.app-header-logo {
  display: block;
  height: 1.75rem;
  width: auto;
}

.app-header-icon {
  display: none;
  height: 1.75rem;
  width: auto;
}

.app-header-nav,
.app-header-end {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.app-header-end {
  margin-left: auto;
  gap: 0.5rem;
}

/* Main places, and ghost buttons that open the menus. */
.app-header-link,
.app-header-button {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.375rem 0.75rem;
  border: 0;
  border-radius: var(--bs-border-radius);
  background: transparent;
  color: var(--bs-secondary-color);
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
}

.app-header-link:hover,
.app-header-button:hover,
.app-header-button[aria-expanded="true"] {
  color: var(--bs-body-color);
  background: var(--bs-tertiary-bg);
}

/* The current place. */
.app-header-link.router-link-active {
  color: var(--bs-primary-text-emphasis);
  background: var(--bs-primary-bg-subtle);
}

.app-header-svg,
.app-header-chevron {
  flex: 0 0 auto;
  width: 1rem;
  height: 1rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.app-header-chevron {
  width: 0.75rem;
  height: 0.75rem;
  opacity: 0.7;
}

.app-header-organisation {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding-right: 0.5rem;
  margin-right: 0.25rem;
  border-right: 1px solid var(--bs-border-color);
  color: var(--bs-secondary-color);
}

.app-header-organisation select {
  width: auto;
  max-width: 14rem;
}

.app-header-organisation-name {
  max-width: 14rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--bs-body-color);
  font-weight: 600;
}

.app-header-avatar {
  display: inline-grid;
  place-items: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 50%;
  background: var(--bs-primary-bg-subtle);
  color: var(--bs-primary-text-emphasis);
  font-size: 0.8125rem;
  font-weight: 700;
}

.app-header-email {
  max-width: 14rem;
  overflow: hidden;
  text-overflow: ellipsis;
}

.app-header-menu {
  min-width: 15rem;
  max-width: 20rem;
}

.app-header-menu .dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.dropdown-menu-end.show {
  right: 0;
  left: auto;
}

/* Phones: the icon instead of the wordmark, menus without their labels. */
@media (max-width: 768px) {
  .app-header {
    gap: 0.75rem;
    padding-inline: 0.75rem;
  }

  .app-header-logo,
  .app-header-collapsible,
  .app-header-organisation-name {
    display: none;
  }

  .app-header-icon {
    display: block;
  }

  .app-header-nav .app-header-link span {
    display: none;
  }

  .app-header-organisation select {
    max-width: 9rem;
  }

  /* A lone organisation's label, without its name, would be just an icon. */
  span.app-header-organisation {
    display: none;
  }
}
</style>
