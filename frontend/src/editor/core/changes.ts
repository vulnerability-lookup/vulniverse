import {
  inject,
} from "vue";

import {
  editorStateKey,
} from "./context/keys";

/*
 * What differs between the record as edited and as last loaded or
 * saved, as dot paths ("containers.cna.affected.0.vendor"), for the
 * "changed" markers on fields, cards, tabs and the record tree. A
 * changed field marks its parents too, so a closed card or another tab
 * still shows there's a change inside. Key order doesn't count; a key
 * set to undefined counts as absent.
 */

function isContainer(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function changedPaths(current: unknown, original: unknown): Set<string> {
  const changed = new Set<string>();
  const join = (path: string, key: string | number) => (path ? `${path}.${key}` : String(key));

  // An added or removed object or list compares against an empty one,
  // so each field inside an added item is marked too.
  const emptyLike = (value: unknown, other: unknown) => (
    value === undefined && isContainer(other) ? (Array.isArray(other) ? [] : {}) : value
  );

  function walk(a: unknown, b: unknown, path: string): boolean {
    if (a === b) return false;

    const left = emptyLike(a, b);
    const right = emptyLike(b, a);
    let differs = true;

    if (Array.isArray(left) && Array.isArray(right)) {
      // walkList first: it records the items' own paths either way.
      differs = walkList(left, right, path) || left !== a || right !== b;
    } else if (isContainer(left) && isContainer(right) && !Array.isArray(left) && !Array.isArray(right)) {
      differs = left !== a || right !== b;

      for (const key of new Set([...Object.keys(left), ...Object.keys(right)])) {
        // Not short-circuited: every changed child gets its own path.
        if (walk(left[key], right[key], join(path, key))) differs = true;
      }
    }

    if (differs && path) changed.add(path);

    return differs;
  }

  /*
   * Lists: an item still found unchanged in the old list counts as
   * unchanged wherever it moved, so removing or inserting one item
   * doesn't mark every item after it. The rest are paired in order and
   * compared field by field; leftovers are added or removed items. The
   * list itself counts as changed if anything, its order included, did.
   * shortcut: an edit plus a removal in the same list can pair the edited
   * item with the wrong old one; a real list diff (LCS) would fix that.
   */
  function walkList(items: unknown[], oldItems: unknown[], path: string): boolean {
    const unmatched = new Map<string, number[]>();

    oldItems.forEach((item, index) => {
      const key = JSON.stringify(item);
      unmatched.set(key, [...(unmatched.get(key) ?? []), index]);
    });

    const matched = items.map((item) => unmatched.get(JSON.stringify(item))?.shift());
    const taken = new Set(matched);
    const leftOver = oldItems.map((_, index) => index).filter((index) => !taken.has(index));
    let differs = items.length !== oldItems.length || matched.some((old, index) => old !== index);

    items.forEach((item, index) => {
      if (matched[index] !== undefined) return;

      const old = leftOver.shift();

      if (walk(item, old === undefined ? undefined : oldItems[old], join(path, index))) differs = true;
    });

    return differs;
  }

  walk(current, original, "");

  return changed;
}


/** Whether the field or item at `path` differs from the last save. */
export function useIsChanged(): (path: string) => boolean {
  // Absent outside VulniverseEditor (e.g. a renderer mounted on its own).
  const state = inject(editorStateKey, null);

  return (path) => state?.changedPaths.value.has(path) ?? false;
}
