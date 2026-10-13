import type {
  InjectionKey,
  Ref,
} from "vue";

import type {
  EditorRepository,
} from "../../contracts";

import type {
  EditorState,
} from "../state";


export type EditorSaveOptions = {
  silent?: boolean;
};


export type EditorSave = (
  options?: EditorSaveOptions,
) => Promise<string | null>;


export const editorStateKey:
  InjectionKey<EditorState> =
    Symbol("vulniverse-editor-state");


export const editorRepositoryKey:
  InjectionKey<
    Readonly<
      Ref<EditorRepository | undefined>
    >
  > =
    Symbol("vulniverse-editor-repository");


export const editorSaveKey:
  InjectionKey<EditorSave> =
    Symbol("vulniverse-editor-save");
