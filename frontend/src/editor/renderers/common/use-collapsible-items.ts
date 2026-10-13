import {
  ref,
  watch,
} from "vue";

import type {
  Ref,
} from "vue";

/*
 * Shared by every array-card renderer: the item just added (always
 * the last one, since addItem appends) starts expanded so its
 * fields are visible immediately; everything else starts collapsed
 * and toggles via its own button.
 */
export function useCollapsibleItems(
  length: Ref<number>,
) {
  const expandedIndices = ref<Set<number>>(new Set());

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
