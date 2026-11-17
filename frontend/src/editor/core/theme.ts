import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
} from "vue";

import type {
  Ref,
} from "vue";

export type ThemePreference = "auto" | "light" | "dark";
export type Theme = "light" | "dark";

/*
 * The editor's colour theme. "light"/"dark" are used as given. "auto"
 * follows the nearest data-bs-theme above the editor — also outside a
 * web component's shadow root, so a host page's own Bootstrap theme
 * switch (e.g. Vulnerability-Lookup's) carries over — and without one,
 * the operating system's setting. Both are watched while mounted.
 */
export function useEditorTheme(
  preference: Ref<ThemePreference>,
  root: Ref<HTMLElement | null>,
): Readonly<Ref<Theme>> {
  const media = typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-color-scheme: dark)")
    : null;

  const systemDark = ref(media?.matches ?? false);
  const pageTheme = ref<string | null>(null);

  function read(): void {
    systemDark.value = media?.matches ?? false;

    const element = root.value;
    const shadowHost = element ? (element.getRootNode() as ShadowRoot).host : undefined;
    // Above the editor itself, which carries its own data-bs-theme.
    const start = shadowHost ?? element?.parentElement;

    pageTheme.value = start?.closest("[data-bs-theme]")?.getAttribute("data-bs-theme") ?? null;
  }

  const observer = new MutationObserver(read);

  onMounted(() => {
    read();
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-bs-theme"],
      subtree: true,
    });
    media?.addEventListener("change", read);
  });

  onBeforeUnmount(() => {
    observer.disconnect();
    media?.removeEventListener("change", read);
  });

  return computed<Theme>(() => {
    if (preference.value !== "auto") return preference.value;
    if (pageTheme.value === "light" || pageTheme.value === "dark") return pageTheme.value;

    return systemDark.value ? "dark" : "light";
  });
}
