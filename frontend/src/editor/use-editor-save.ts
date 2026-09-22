import {
  inject,
} from "vue";

import {
  editorSaveKey,
} from "./editor-context";

/**
 * See editorSaveKey. Always provided by VulniverseEditor.ce.vue, so a
 * missing value here means this composable was called outside it —
 * a usage error, not a normal degraded state (unlike
 * useEditorRepository(), where "no repository" is expected).
 */
export function useEditorSave(): (options?: { silent?: boolean }) => Promise<string | null> {
  const save = inject(editorSaveKey);

  if (!save) {
    throw new Error(
      "This component must be rendered inside "
      + "VulniverseEditor.",
    );
  }

  return save;
}
