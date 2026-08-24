import type {
  InjectionKey,
  Ref,
} from "vue";

import type {
  EditorRepository,
} from "./contracts";

import type {
  EditorState,
} from "./use-editor-state";

export const editorStateKey:
  InjectionKey<EditorState> =
    Symbol("vulniverse-editor-state");

export const editorRepositoryKey:
  InjectionKey<Ref<EditorRepository | undefined>> =
    Symbol("vulniverse-editor-repository");
