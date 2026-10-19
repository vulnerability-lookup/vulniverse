import {
  inject,
} from "vue";

import type {
  EditorSave,
} from "./keys";

import {
  editorSaveKey,
} from "./keys";


export function useEditorSave():
  EditorSave {
  const save =
    inject(editorSaveKey);

  if (!save) {
    throw new Error(
      "useEditorSave() must be used inside VulniverseEditor.",
    );
  }

  return save;
}
