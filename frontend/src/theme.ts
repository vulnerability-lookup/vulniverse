import {
  computed,
  ref,
  watchEffect,
} from "vue";

import type {
  Theme,
  ThemePreference,
} from "@/editor/core/theme";

/*
 * The standalone app's theme: the user's choice (system, light, dark),
 * remembered in this browser, applied as Bootstrap's data-bs-theme on
 * <html>. The editor follows it by itself (its theme "auto").
 * Imported first in main.ts, so the page has its theme before it draws.
 */
const STORAGE_KEY = "vulniverse-theme";

const media = window.matchMedia("(prefers-color-scheme: dark)");
const systemDark = ref(media.matches);

media.addEventListener("change", (event) => {
  systemDark.value = event.matches;
});

function stored(): ThemePreference {
  try {
    const value = localStorage.getItem(STORAGE_KEY);

    return value === "light" || value === "dark" ? value : "auto";
  } catch {
    // Storage blocked (private mode, policy): just follow the system.
    return "auto";
  }
}

export const themePreference = ref<ThemePreference>(stored());

export const appTheme = computed<Theme>(() => {
  if (themePreference.value !== "auto") return themePreference.value;

  return systemDark.value ? "dark" : "light";
});

watchEffect(() => {
  document.documentElement.setAttribute("data-bs-theme", appTheme.value);

  try {
    if (themePreference.value === "auto") localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, themePreference.value);
  } catch {
    // Not remembered then; the choice still holds for this visit.
  }
});

const ORDER: ThemePreference[] = ["auto", "light", "dark"];

/** System → light → dark → system. */
export function nextTheme(): void {
  themePreference.value = ORDER[(ORDER.indexOf(themePreference.value) + 1) % ORDER.length]!;
}
