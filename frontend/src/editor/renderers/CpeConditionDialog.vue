<script setup lang="ts">
import {
  ref,
} from "vue";

import {
  fromVersionFields,
  toVersionFields,
} from "./cpe-applicability";

import type {
  CpeMatch,
  VersionConstraintUi,
} from "./cpe-applicability";

const emit = defineEmits<{
  apply: [
    match: CpeMatch,
  ];
}>();

const dialog = ref<HTMLDialogElement | null>(null);
const title = ref("Add CPE condition");

const role = ref<"vulnerable" | "environment">("vulnerable");
const criteria = ref("");

const versionMode = ref<VersionConstraintUi["mode"]>("any");
const exactValue = ref("");
const fromValue = ref("");
const fromInclusive = ref(true);
const toValue = ref("");
const toInclusive = ref(false);

const showAdvanced = ref(false);
const matchCriteriaId = ref("");

/*
 * initial is a full CpeMatch when editing an existing condition,
 * omitted when adding a new one — in both cases this fully resets the
 * dialog's local state so a reused dialog instance never leaks a
 * previous condition's values into the next one.
 */
function open(
  initial?: CpeMatch,
): void {
  title.value = initial ? "Edit CPE condition" : "Add CPE condition";
  role.value = initial?.vulnerable === false ? "environment" : "vulnerable";
  criteria.value = initial?.criteria ?? "";
  matchCriteriaId.value = initial?.matchCriteriaId ?? "";
  showAdvanced.value = Boolean(initial?.matchCriteriaId);

  const constraint = initial ? fromVersionFields(initial) : { mode: "any" as const };

  versionMode.value = constraint.mode;
  exactValue.value = constraint.mode === "exact" ? constraint.value : "";
  fromValue.value = constraint.mode === "range" ? constraint.from?.value ?? "" : "";
  fromInclusive.value = constraint.mode === "range" ? constraint.from?.inclusive ?? true : true;
  toValue.value = constraint.mode === "range" ? constraint.to?.value ?? "" : "";
  toInclusive.value = constraint.mode === "range" ? constraint.to?.inclusive ?? false : false;

  dialog.value?.showModal();
}

function close(): void {
  dialog.value?.close();
}

function handleSubmit(): void {
  const trimmedCriteria = criteria.value.trim();

  if (!trimmedCriteria) {
    return;
  }

  const constraint: VersionConstraintUi =
    versionMode.value === "exact"
      ? { mode: "exact", value: exactValue.value.trim() }
      : versionMode.value === "range"
        ? {
          mode: "range",
          from: fromValue.value.trim()
            ? { value: fromValue.value.trim(), inclusive: fromInclusive.value }
            : undefined,
          to: toValue.value.trim()
            ? { value: toValue.value.trim(), inclusive: toInclusive.value }
            : undefined,
        }
        : { mode: "any" };

  const trimmedMatchCriteriaId = matchCriteriaId.value.trim();

  emit("apply", {
    vulnerable: role.value === "vulnerable",
    criteria: trimmedCriteria,
    ...toVersionFields(constraint),
    ...(trimmedMatchCriteriaId ? { matchCriteriaId: trimmedMatchCriteriaId } : {}),
  });

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
  >
    <form @submit.prevent="handleSubmit">
      <div class="editor-dialog-header">
        <h2 class="h6 mb-0">
          {{ title }}
        </h2>

        <button
          type="button"
          class="btn-close"
          aria-label="Close"
          @click="close"
        />
      </div>

      <div class="editor-dialog-body">
        <label class="form-label">Role</label>

        <div class="mb-3">
          <div class="form-check">
            <input
              id="cpe-role-vulnerable"
              v-model="role"
              class="form-check-input"
              type="radio"
              value="vulnerable"
            >

            <label
              class="form-check-label"
              for="cpe-role-vulnerable"
            >
              Vulnerable product
            </label>
          </div>

          <div class="form-check">
            <input
              id="cpe-role-environment"
              v-model="role"
              class="form-check-input"
              type="radio"
              value="environment"
            >

            <label
              class="form-check-label"
              for="cpe-role-environment"
            >
              Required environment (e.g. an OS or platform this applies on)
            </label>
          </div>
        </div>

        <label
          for="cpe-criteria"
          class="form-label"
        >
          CPE
        </label>

        <input
          id="cpe-criteria"
          v-model="criteria"
          class="form-control mb-1"
          required
          placeholder="cpe:2.3:a:vendor:product:*:*:*:*:*:*:*:*"
        >

        <p class="form-text mb-3">
          Entered manually — this editor has no CPE dictionary/search to
          pick from yet.
        </p>

        <label class="form-label">Version constraint</label>

        <div class="mb-3">
          <div class="form-check">
            <input
              id="cpe-version-any"
              v-model="versionMode"
              class="form-check-input"
              type="radio"
              value="any"
            >

            <label
              class="form-check-label"
              for="cpe-version-any"
            >
              Any version
            </label>
          </div>

          <div class="form-check">
            <input
              id="cpe-version-exact"
              v-model="versionMode"
              class="form-check-input"
              type="radio"
              value="exact"
            >

            <label
              class="form-check-label"
              for="cpe-version-exact"
            >
              Exact version
            </label>
          </div>

          <input
            v-if="versionMode === 'exact'"
            v-model="exactValue"
            class="form-control form-control-sm ms-4 mt-1"
            style="width: auto"
            placeholder="1.2.3"
          >

          <div class="form-check">
            <input
              id="cpe-version-range"
              v-model="versionMode"
              class="form-check-input"
              type="radio"
              value="range"
            >

            <label
              class="form-check-label"
              for="cpe-version-range"
            >
              Range
            </label>
          </div>

          <div
            v-if="versionMode === 'range'"
            class="row g-2 ms-4 mt-1"
          >
            <div class="col-auto">
              <label class="form-label small mb-1">From</label>

              <div class="input-group input-group-sm">
                <input
                  v-model="fromValue"
                  class="form-control"
                  style="max-width: 10rem"
                  placeholder="1.0.0"
                >

                <select
                  v-model="fromInclusive"
                  class="form-select"
                  style="max-width: 8rem"
                >
                  <option :value="true">
                    Inclusive
                  </option>

                  <option :value="false">
                    Exclusive
                  </option>
                </select>
              </div>
            </div>

            <div class="col-auto">
              <label class="form-label small mb-1">To</label>

              <div class="input-group input-group-sm">
                <input
                  v-model="toValue"
                  class="form-control"
                  style="max-width: 10rem"
                  placeholder="2.0.0"
                >

                <select
                  v-model="toInclusive"
                  class="form-select"
                  style="max-width: 8rem"
                >
                  <option :value="true">
                    Inclusive
                  </option>

                  <option :value="false">
                    Exclusive
                  </option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <button
          type="button"
          class="btn btn-link btn-sm ps-0 mb-3"
          @click="showAdvanced = !showAdvanced"
        >
          {{ showAdvanced ? "▾" : "▸" }} Advanced
        </button>

        <div
          v-if="showAdvanced"
          class="mb-3"
        >
          <label
            for="cpe-match-criteria-id"
            class="form-label"
          >
            Match Criteria ID
          </label>

          <input
            id="cpe-match-criteria-id"
            v-model="matchCriteriaId"
            class="form-control"
            placeholder="123e4567-e89b-12d3-a456-426614174000"
          >
        </div>

        <div class="d-flex justify-content-end gap-2">
          <button
            type="button"
            class="btn btn-outline-secondary"
            @click="close"
          >
            Cancel
          </button>

          <button
            type="submit"
            class="btn btn-primary"
            :disabled="!criteria.trim()"
          >
            Save
          </button>
        </div>
      </div>
    </form>
  </dialog>
</template>
