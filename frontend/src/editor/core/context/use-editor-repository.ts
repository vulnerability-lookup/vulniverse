import {
  inject,
  ref,
} from "vue";

import {
  editorRepositoryKey,
} from "./keys";

import type {
  Ref,
} from "vue";

import type {
  EditorRepository,
} from "../../contracts";

export function useEditorRepository():
  Readonly<
    Ref<EditorRepository | undefined>
  > {
  const repository =
    inject(editorRepositoryKey);

  if (repository) {
    return repository;
  }

  return ref<EditorRepository>();
}
