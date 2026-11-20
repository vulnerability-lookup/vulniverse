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
  return diffPaths(current, original).changed;
}

/**
 * One change since the last save, for the list of unsaved changes:
 * a field that changed, or an object or list item added or removed as a
 * whole (its fields aren't listed one by one). `path` is where it is in
 * the record as edited; for a removed list item, where it was in the
 * saved list (`fromList`), so undoing it puts it back there.
 */
export interface RecordChange {
  kind: "changed" | "added" | "removed";
  path: string;
  /** As saved; undefined if it wasn't there. */
  before?: unknown;
  /** As edited; undefined if it's gone. */
  after?: unknown;
  fromList?: boolean;
}

/**
 * changedPaths, plus `added`: the objects and lists that are new (no
 * counterpart in the original), e.g. an added card, for its "New" badge;
 * and `changes`, the list of what changed.
 */
export function diffPaths(
  current: unknown,
  original: unknown,
): { changed: Set<string>; added: Set<string>; changes: RecordChange[] } {
  const changed = new Set<string>();
  const added = new Set<string>();
  const changes: RecordChange[] = [];
  const join = (path: string, key: string | number) => (path ? `${path}.${key}` : String(key));

  // An added or removed object or list compares against an empty one,
  // so each field inside an added item is marked too.
  const emptyLike = (value: unknown, other: unknown) => (
    value === undefined && isContainer(other) ? (Array.isArray(other) ? [] : {}) : value
  );

  // `quiet`: inside an added or removed object, which is listed once.
  function walk(a: unknown, b: unknown, path: string, quiet = false): boolean {
    if (a === b) return false;

    const isAdded = Boolean(path) && b === undefined && isContainer(a);
    const isRemoved = Boolean(path) && a === undefined && isContainer(b);

    if (isAdded) added.add(path);
    if (!quiet && isAdded) changes.push({ kind: "added", path, after: a });
    if (!quiet && isRemoved) {
      // A list removed as a whole (e.g. its last item, where it must not be
      // empty) counts as its items removed, like a list that's still there.
      if (Array.isArray(b) && b.length) {
        b.forEach((item, index) => {
          changes.push({ kind: "removed", path: join(path, index), before: item, fromList: true });
        });
      } else {
        changes.push({ kind: "removed", path, before: b });
      }
    }

    const inner = quiet || isAdded || isRemoved;
    const left = emptyLike(a, b);
    const right = emptyLike(b, a);
    let differs = true;

    if (Array.isArray(left) && Array.isArray(right)) {
      const listed = changes.length;
      // walkList first: it records the items' own paths either way.
      differs = walkList(left, right, path, inner) || left !== a || right !== b;

      // Nothing inside changed, added or went: only the order did.
      if (differs && !inner && changes.length === listed) {
        changes.push({ kind: "changed", path, before: b, after: a });
      }
    } else if (isContainer(left) && isContainer(right) && !Array.isArray(left) && !Array.isArray(right)) {
      differs = left !== a || right !== b;

      for (const key of new Set([...Object.keys(left), ...Object.keys(right)])) {
        // Not short-circuited: every changed child gets its own path.
        if (walk(left[key], right[key], join(path, key), inner)) differs = true;
      }
    } else if (!inner && path) {
      changes.push({ kind: "changed", path, before: b, after: a });
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
  function walkList(items: unknown[], oldItems: unknown[], path: string, quiet: boolean): boolean {
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

      if (walk(item, old === undefined ? undefined : oldItems[old], join(path, index), quiet)) differs = true;
    });

    // Old items nothing was paired with: removed.
    if (!quiet) {
      leftOver.forEach((old) => {
        changes.push({ kind: "removed", path: join(path, old), before: oldItems[old], fromList: true });
      });
    }

    return differs;
  }

  walk(current, original, "");

  return { changed, added, changes };
}

/**
 * Sets `path` in `record` to `value`, creating objects and lists on the
 * way; `undefined` removes it (from a list: the item).
 */
export function setAtPath(record: Record<string, unknown>, path: string, value: unknown): void {
  const keys = path.split(".");
  const last = keys.pop()!;
  let parent: Record<string, unknown> | unknown[] = record;

  keys.forEach((key, index) => {
    const container = parent as Record<string, unknown>;
    if (typeof container[key] !== "object" || container[key] === null) {
      // The next key decides: a number means a list.
      container[key] = /^\d+$/.test(keys[index + 1] ?? last) ? [] : {};
    }
    parent = container[key] as Record<string, unknown>;
  });

  if (value !== undefined) {
    // A JSON copy: the value may hold Vue proxies, which structuredClone can't copy.
    (parent as Record<string, unknown>)[last] = JSON.parse(JSON.stringify(value));
  } else if (Array.isArray(parent)) {
    parent.splice(Number(last), 1);
  } else {
    delete (parent as Record<string, unknown>)[last];
  }
}

/** Takes one change back in `record` (a plain copy of the edited record). */
export function undoChange(record: Record<string, unknown>, change: RecordChange): void {
  if (change.fromList) {
    const at = change.path.lastIndexOf(".");
    const list = change.path.slice(0, at).split(".")
      .reduce<unknown>((value, key) => (value as Record<string, unknown> | undefined)?.[key], record);

    if (Array.isArray(list)) {
      const index = Number(change.path.slice(at + 1));
      // Back where it was, or at the end if the list is shorter now.
      list.splice(Math.min(index, list.length), 0, JSON.parse(JSON.stringify(change.before)));
    } else {
      // The whole list is gone: it comes back with this item.
      setAtPath(record, change.path.slice(0, at), [change.before]);
    }
    return;
  }

  setAtPath(record, change.path, change.kind === "added" ? undefined : change.before);
}


/** Whether the field or item at `path` differs from the last save. */
export function useIsChanged(): (path: string) => boolean {
  // Absent outside VulniverseEditor (e.g. a renderer mounted on its own).
  const state = inject(editorStateKey, null);

  return (path) => state?.changedPaths.value.has(path) ?? false;
}

/** A card's change classes: `editor-changed`, and `editor-added` if it's new. */
export function useChangeClass(): (path: string) => Record<string, boolean> {
  const state = inject(editorStateKey, null);

  return (path) => ({
    "editor-changed": state?.changedPaths.value.has(path) ?? false,
    "editor-added": state?.addedPaths.value.has(path) ?? false,
  });
}

/**
 * How many fields changed inside `path`: the innermost changed paths
 * under it, as a closed card's summary.
 */
export function countChanges(changed: Set<string>, path: string): number {
  const inside = [...changed].filter((other) => other.startsWith(`${path}.`));

  return inside.filter((other) => !inside.some((deeper) => deeper.startsWith(`${other}.`))).length;
}

/** Undoes one change in the editor's record (a new copy, so everything updates). */
export function useUndoChange(): (change: RecordChange) => void {
  const state = inject(editorStateKey, null);

  return (change) => {
    if (!state?.record.value) return;

    // Records are plain JSON, but after form edits they hold nested Vue
    // proxies, which structuredClone (even after toRaw) can't copy.
    const record = JSON.parse(JSON.stringify(state.record.value)) as Record<string, unknown>;
    undoChange(record, change);
    state.record.value = record as typeof state.record.value;
  };
}
