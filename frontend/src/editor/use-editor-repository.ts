import {
  inject,
  ref,
} from "vue";

import {
  editorRepositoryKey,
} from "./editor-context";

import type {
  Ref,
} from "vue";

import type {
  EditorRepository,
} from "./contracts";

/**
 * Unlike useEditorContext(), a missing repository is a normal,
 * expected state (e.g. no repository configured yet, or a host that
 * only implements the required EditorRepository methods) — callers
 * are expected to degrade gracefully, not treat it as a usage error.
 * Returns a ref (not a snapshot) since the host-supplied repository
 * prop can in principle change after mount.
 */
export function useEditorRepository(): Ref<EditorRepository | undefined> {
  return inject(editorRepositoryKey, ref(undefined));
}
