<script setup lang="ts">
import {
  ref,
} from "vue";

/*
 * The Reject transition's dialog (see TransitionDialog in contracts):
 * open() resolves with the trimmed reason, or null when cancelled.
 */
const dialog = ref<HTMLDialogElement | null>(null);
const reason = ref("");

let resolve: ((value: string | null) => void) | null = null;

function open(): Promise<string | null> {
  reason.value = "";
  dialog.value?.showModal();

  return new Promise((done) => {
    resolve = done;
  });
}

// Every way of closing (Cancel, ×, Escape) ends here; a submit has
// already resolved with the reason.
function finish(value: string | null): void {
  resolve?.(value);
  resolve = null;
}

function close(): void {
  dialog.value?.close();
}

function handleSubmit(): void {
  const trimmed = reason.value.trim();

  if (!trimmed) {
    return;
  }

  finish(trimmed);
  close();
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
          Reject this record
        </h2>

        <button
          type="button"
          class="btn-close"
          aria-label="Close"
          @click="close"
        />
      </div>

      <div class="editor-dialog-body">
        <p class="text-secondary">
          Explain why this record is being rejected. This replaces
          the record's normal content with a rejection reason — it
          can't be undone by editing fields back in afterward.
        </p>

        <label
          for="reject-reason"
          class="form-label"
        >
          Reason
        </label>

        <textarea
          id="reject-reason"
          v-model="reason"
          class="form-control"
          rows="4"
          required
          placeholder="e.g. Duplicate of GCVE-0-2026-00050"
        />

        <div class="d-flex justify-content-end gap-2 mt-3">
          <button
            type="button"
            class="btn btn-outline-secondary"
            @click="close"
          >
            Cancel
          </button>

          <button
            type="submit"
            class="btn btn-outline-danger"
          >
            Reject
          </button>
        </div>
      </div>
    </form>
  </dialog>
</template>
