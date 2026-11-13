<script setup lang="ts">
import {
  computed,
  ref,
} from "vue";

import type {
  EditorContext,
} from "../contracts";

import {
  currentVersion,
  isDraftVersion,
  isReleased,
  nextVersion,
  versioning,
} from "./csaf-release";

import type {
  ReleaseInput,
  ReleaseKind,
  ReleaseStatus,
} from "./csaf-release";

/*
 * The CSAF Release/Update transitions' dialog (see TransitionDialog in
 * contracts): open() resolves with a ReleaseInput, or null when
 * cancelled. A draft gets its first release (1.0.0 or 1); a released
 * document a new major/minor/patch version.
 */
const dialog = ref<HTMLDialogElement | null>(null);

const update = ref(false);
const integer = ref(false);
const version = ref("");
const draftEntries = ref<string[]>([]);
const kind = ref<ReleaseKind>("initial");
const status = ref<ReleaseStatus>("final");
const summary = ref("");

const target = computed(() => nextVersion(version.value, kind.value));

const KINDS: { kind: ReleaseKind; hint: string }[] = [
  { kind: "patch", hint: "corrections only" },
  { kind: "minor", hint: "new information, e.g. products or fixes" },
  { kind: "major", hint: "readers must check their affected assets again" },
];

let resolve: ((value: ReleaseInput | null) => void) | null = null;

function open(
  context: EditorContext,
): Promise<ReleaseInput | null> {
  const record = context.record;
  const tracking = ((record.document ?? {}) as Record<string, any>).tracking ?? {}; // eslint-disable-line @typescript-eslint/no-explicit-any -- JSON document

  update.value = isReleased(record);
  integer.value = versioning(record) === "integer";
  version.value = currentVersion(record);
  kind.value = update.value ? (integer.value ? "major" : "minor") : "initial";
  status.value = tracking.status === "interim" ? "interim" : "final";
  summary.value = update.value ? "" : "Initial release.";
  draftEntries.value = update.value
    ? []
    : (Array.isArray(tracking.revision_history) ? tracking.revision_history : [])
        .map((entry: { number?: unknown }) => entry?.number)
        .filter((number: unknown): number is string => isDraftVersion(number));

  dialog.value?.showModal();

  return new Promise((done) => {
    resolve = done;
  });
}

// Every way of closing (Cancel, ×, Escape) ends here; a submit has
// already resolved with the input.
function finish(value: ReleaseInput | null): void {
  resolve?.(value);
  resolve = null;
}

function handleSubmit(): void {
  const trimmed = summary.value.trim();

  if (!trimmed) {
    return;
  }

  finish({ kind: kind.value, status: status.value, summary: trimmed });
  dialog.value?.close();
}

defineExpose({
  open,
});
</script>

<template>
  <dialog
    ref="dialog"
    class="editor-dialog"
    @close="finish(null)"
  >
    <form @submit.prevent="handleSubmit">
      <div class="editor-dialog-header">
        <h2 class="h6 mb-0">
          {{ update ? "Release a new version" : "Release this advisory" }}
        </h2>

        <button
          type="button"
          class="btn-close"
          aria-label="Close"
          @click="dialog?.close()"
        />
      </div>

      <div class="editor-dialog-body">
        <p class="mb-3">
          Version
          <code>{{ version || "–" }}</code>
          →
          <code>{{ target }}</code>
        </p>

        <fieldset
          v-if="update && !integer"
          class="mb-3"
        >
          <legend class="form-label fs-6">
            Change
          </legend>

          <div
            v-for="option in KINDS"
            :key="option.kind"
            class="form-check"
          >
            <input
              :id="`csaf-release-${option.kind}`"
              v-model="kind"
              class="form-check-input"
              type="radio"
              :value="option.kind"
            >

            <label
              class="form-check-label"
              :for="`csaf-release-${option.kind}`"
            >
              {{ option.kind }}
              <code>{{ nextVersion(version, option.kind) }}</code>
              <span class="text-secondary"> · {{ option.hint }}</span>
            </label>
          </div>
        </fieldset>

        <fieldset class="mb-3">
          <legend class="form-label fs-6">
            Status
          </legend>

          <div class="form-check form-check-inline">
            <input
              id="csaf-release-final"
              v-model="status"
              class="form-check-input"
              type="radio"
              value="final"
            >
            <label
              class="form-check-label"
              for="csaf-release-final"
            >final</label>
          </div>

          <div class="form-check form-check-inline">
            <input
              id="csaf-release-interim"
              v-model="status"
              class="form-check-input"
              type="radio"
              value="interim"
            >
            <label
              class="form-check-label"
              for="csaf-release-interim"
            >interim <span class="text-secondary">· expected to change soon</span></label>
          </div>
        </fieldset>

        <label
          for="csaf-release-summary"
          class="form-label"
        >
          Summary <span class="text-danger">*</span>
        </label>

        <textarea
          id="csaf-release-summary"
          v-model="summary"
          class="form-control"
          rows="2"
          required
          :placeholder="update ? 'e.g. Added fixed version 2.4.1.' : ''"
        />

        <p class="small text-secondary mt-2 mb-0">
          The release date is the time you confirm.
          <template v-if="draftEntries.length">
            The draft entries {{ draftEntries.join(", ") }} in the revision
            history are replaced by one entry {{ target }}.
          </template>
        </p>

        <div class="d-flex justify-content-end gap-2 mt-3">
          <button
            type="button"
            class="btn btn-outline-secondary"
            @click="dialog?.close()"
          >
            Cancel
          </button>

          <button
            type="submit"
            class="btn btn-success"
          >
            Release {{ target }}
          </button>
        </div>
      </div>
    </form>
  </dialog>
</template>
