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

/*
 * Saves the record exactly the way the header's own Save button
 * does (create-or-update, keeping the current draft/published
 * state), resolving to the saved identifier — or null if the save
 * didn't happen/failed, in which case the failure is already
 * surfaced through the usual state.saveError/@error path, so a
 * caller just needs to stop rather than handle it again. Lets a
 * built-in panel (e.g. CnaPublicationPanel.vue) silently save an
 * unsaved record the first time it actually needs an identifier,
 * instead of requiring a manual Save first.
 *
 * `silent: true` skips the "loaded" emit — for a record that's
 * never been saved, the host page (e.g. NewRecordPage.vue) reacts
 * to "loaded" by navigating to the record's own URL immediately,
 * which would tear this component down mid-action before a caller
 * like CnaPublicationPanel.vue has finished (reserving, applying the
 * result, then saving again for real). Use it only for an internal
 * "just get me some identifier" step, never for a save the user
 * should see reflected in the URL.
 */
export const editorSaveKey:
  InjectionKey<(options?: { silent?: boolean }) => Promise<string | null>> =
    Symbol("vulniverse-editor-save");
