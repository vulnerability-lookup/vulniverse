import {
  inject,
} from "vue";

import {
  editorStateKey,
} from "./keys";

import type {
  EditorState,
} from "../state";

export function useEditorContext(): EditorState {
  const state = inject(editorStateKey);

  if (!state) {
    throw new Error(
      "This component must be rendered inside "
      + "VulniverseEditor.",
    );
  }

  return state;
}
