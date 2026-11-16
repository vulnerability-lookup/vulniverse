import {
  inject,
  ref,
  watch,
} from "vue";

import {
  editorStateKey,
} from "../../core/context/keys";

import {
  itemIndex,
} from "../../core/reveal";

import type {
  Ref,
} from "vue";

/*
 * Shared by every array-card renderer: the item just added (always
 * the last one, since addItem appends) starts expanded so its
 * fields are visible immediately; everything else starts collapsed
 * and toggles via its own button. With the array's data path, the item
 * a reveal request points into (the record tree, a validation error)
 * opens too.
 */
export function useCollapsibleItems(
  length: Ref<number>,
  path?: Ref<string>,
) {
  const expandedIndices = ref<Set<number>>(new Set());

  // Absent outside VulniverseEditor (e.g. a renderer mounted on its own).
  const state = inject(editorStateKey, null);

  if (path && state) {
    watch(
      [() => state.reveal.value, path],
      ([request, arrayPath]) => {
        const index = request ? itemIndex(request.path, arrayPath) : null;

        if (index !== null) {
          expandedIndices.value.add(index);
        }
      },
      { immediate: true },
    );
  }

  watch(
    length,
    (currentLength, previousLength) => {
      if (previousLength === undefined) {
        if (currentLength > 0) {
          expandedIndices.value.add(currentLength - 1);
        }

        return;
      }

      if (currentLength > previousLength) {
        expandedIndices.value.add(currentLength - 1);
      }
    },
    {
      immediate: true,
    },
  );

  function isExpanded(
    index: number,
  ): boolean {
    return expandedIndices.value.has(index);
  }

  function toggle(
    index: number,
  ): void {
    if (expandedIndices.value.has(index)) {
      expandedIndices.value.delete(index);
    } else {
      expandedIndices.value.add(index);
    }
  }

  return {
    isExpanded,
    toggle,
  };
}
