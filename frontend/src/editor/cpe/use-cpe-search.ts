import {
  ref,
} from "vue";

const DEBOUNCE_MS = 300;
const MIN_QUERY_LENGTH = 2;

/*
 * Shared live-search behavior for both the "vendor" autocomplete
 * (AffectedRenderer.vue) and the CPE-string autocomplete
 * (CpeConditionDialog.vue): debounced so typing doesn't fire one
 * request per keystroke, and request-token guarded so a slow early
 * response can never clobber a later, faster one. The search
 * function itself is supplied by the call site (already bound to
 * whatever EditorRepository method applies) so this stays agnostic
 * of which CPE Editor endpoint is being queried.
 *
 * A short/blank query clears results locally without calling search
 * at all — the backend applies the same MIN_QUERY_LENGTH threshold,
 * but checking here too avoids a pointless debounce-timer round trip
 * on every first keystroke.
 */
export function useCpeSearch<T>(
  search: (query: string) => Promise<T[]>,
) {
  const results = ref<T[]>([]);
  const loading = ref(false);
  const open = ref(false);
  // Distinct from "loading" with zero results so the dropdown can
  // say "search failed" instead of silently looking like "no
  // matches" — the CPE Editor's broad search can legitimately take
  // 10s+ or occasionally time out against its ~2.1M-row dictionary.
  const failed = ref(false);

  let debounceTimer: ReturnType<typeof setTimeout> | undefined;
  let requestToken = 0;

  function clearTimer(): void {
    if (debounceTimer !== undefined) {
      clearTimeout(debounceTimer);
      debounceTimer = undefined;
    }
  }

  function runSearch(term: string): void {
    const token = ++requestToken;

    loading.value = true;
    failed.value = false;

    search(term)
      .then((items) => {
        if (token === requestToken) {
          results.value = items;
        }
      })
      .catch(() => {
        if (token === requestToken) {
          results.value = [];
          failed.value = true;
        }
      })
      .finally(() => {
        if (token === requestToken) {
          loading.value = false;
        }
      });
  }

  function onQueryChange(
    value: string,
  ): void {
    open.value = true;
    clearTimer();

    const term = value.trim();

    if (term.length < MIN_QUERY_LENGTH) {
      // Invalidate any in-flight/debounced search so its result
      // can't land after the query has already been cleared.
      requestToken++;
      loading.value = false;
      failed.value = false;
      results.value = [];

      return;
    }

    debounceTimer = setTimeout(
      () => runSearch(term),
      DEBOUNCE_MS,
    );
  }

  function show(): void {
    open.value = true;
  }

  function hide(): void {
    open.value = false;
  }

  function reset(): void {
    clearTimer();
    requestToken++;
    loading.value = false;
    failed.value = false;
    results.value = [];
    open.value = false;
  }

  return {
    results,
    loading,
    failed,
    open,
    onQueryChange,
    show,
    hide,
    reset,
  };
}
