<script setup lang="ts">
import {
  computed,
  onUnmounted,
  ref,
  watch,
} from "vue";

import {
  useEditorContext,
} from "../core/context";


const state = useEditorContext();


const blockingErrors = computed(() => {
  return state.validationErrors.value.filter(
    (error) =>
      (error.severity ?? "error") === "error",
  );
});


const validationWarnings = computed(() => {
  return state.validationErrors.value.filter(
    (error) =>
      error.severity === "warning",
  );
});


const blockingErrorsDismissed = ref(false);
const validationWarningsDismissed = ref(false);


watch(
  state.validationErrors,
  () => {
    blockingErrorsDismissed.value = false;
    validationWarningsDismissed.value = false;
  },
);


const SUCCESS_TOAST_DURATION_MS = 4000;

let successToastTimeout:
  ReturnType<typeof setTimeout> | undefined;


watch(
  state.validationSucceeded,
  (succeeded) => {
    clearTimeout(successToastTimeout);

    if (!succeeded) {
      return;
    }

    successToastTimeout = setTimeout(
      () => {
        state.validationSucceeded.value = false;
      },
      SUCCESS_TOAST_DURATION_MS,
    );
  },
);


onUnmounted(() => {
  clearTimeout(successToastTimeout);
});
</script>

<template>
  <div class="validation-toast-stack">
    <div
      v-if="state.saveError.value"
      class="alert alert-danger alert-dismissible mb-2 shadow-sm"
      role="alert"
    >
      {{ state.saveError.value.message }}

      <button
        type="button"
        class="btn-close"
        aria-label="Close"
        @click="state.saveError.value = null"
      />
    </div>

    <div
      v-if="state.validationSucceeded.value"
      class="alert alert-success alert-dismissible mb-2 shadow-sm"
      role="status"
    >
      The record is valid.

      <button
        type="button"
        class="btn-close"
        aria-label="Close"
        @click="state.validationSucceeded.value = false"
      />
    </div>

    <div
      v-if="
        blockingErrors.length &&
        !blockingErrorsDismissed
      "
      class="alert alert-warning alert-dismissible mb-2 shadow-sm"
      role="alert"
    >
      <button
        type="button"
        class="btn-close"
        aria-label="Close"
        @click="blockingErrorsDismissed = true"
      />

      <p class="mb-2">
        The record has
        {{ blockingErrors.length }}
        validation
        {{
          blockingErrors.length === 1
            ? "error"
            : "errors"
        }}.
      </p>

      <ul class="mb-0">
        <li
          v-for="(error, index) in blockingErrors"
          :key="index"
        >
          <code>
            {{ error.path.join(".") || "record" }}
          </code>
          — {{ error.message }}
        </li>
      </ul>
    </div>

    <div
      v-if="
        validationWarnings.length &&
        !validationWarningsDismissed
      "
      class="alert alert-info alert-dismissible mb-2 shadow-sm"
      role="alert"
    >
      <button
        type="button"
        class="btn-close"
        aria-label="Close"
        @click="validationWarningsDismissed = true"
      />

      <p class="mb-2">
        {{ validationWarnings.length }}
        validation
        {{
          validationWarnings.length === 1
            ? "warning"
            : "warnings"
        }}
        (won't block saving).
      </p>

      <ul class="mb-0">
        <li
          v-for="(warning, index) in validationWarnings"
          :key="index"
        >
          <code>
            {{ warning.path.join(".") || "record" }}
          </code>
          — {{ warning.message }}
        </li>
      </ul>
    </div>
  </div>
</template>
