<script setup lang="ts">
import {
  computed,
  ref,
} from "vue";

import osvSchema from
  "@/generated/schemas/osv-1.9.2/authoring.schema.json";

import type {
  ConversionTarget,
  EditorContext,
} from "../contracts";

/*
 * The "Convert to…" action's dialog (see TransitionDialog in contracts):
 * open() resolves with { target, ecosystem }, or null when cancelled.
 */
export interface ConvertInput {
  target: ConversionTarget;
  ecosystem: string;
}

// OSV's ecosystems, from the schema's ecosystem pattern "^(A|B|…)(:.+)?$".
const ECOSYSTEMS = (() => {
  const pattern = (osvSchema as unknown as {
    properties: { affected: { items: { properties: { package: { properties: {
      ecosystem: { pattern?: string };
    } } } } } };
  }).properties.affected.items.properties.package.properties.ecosystem.pattern ?? "";
  const names = /^\^\((.*)\)\(:\.\+\)\?\$$/.exec(pattern)?.[1] ?? "";

  return names.split("|").map((name) => name.replace(/\\\./g, ".")).filter(Boolean).sort(
    (a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }),
  );
})();

const dialog = ref<HTMLDialogElement | null>(null);
const source = ref("");
const target = ref<ConversionTarget>("csaf");
const ecosystem = ref("");
const productsWithoutPurl = ref<string[]>([]);
const gcveId = ref("");

// OSV needs an ecosystem for every product without a package URL.
const needsEcosystem = computed(() => target.value === "osv" && productsWithoutPurl.value.length > 0);

let resolve: ((value: ConvertInput | null) => void) | null = null;

function open(
  context: EditorContext,
): Promise<ConvertInput | null> {
  const record = context.record as {
    cveMetadata?: { cveId?: string; vulnId?: string };
    containers?: { cna?: { affected?: { product?: string; packageURL?: string }[]; x_gcve?: { vulnId?: string }[] } };
  };
  const cna = record.containers?.cna ?? {};

  gcveId.value = cna.x_gcve?.[0]?.vulnId ?? record.cveMetadata?.vulnId ?? "";
  source.value = gcveId.value || record.cveMetadata?.cveId || "this record";
  productsWithoutPurl.value = (Array.isArray(cna.affected) ? cna.affected : [])
    .filter((affected) => !affected?.packageURL)
    .map((affected) => affected?.product || "unnamed product");
  target.value = "csaf";
  ecosystem.value = "";

  dialog.value?.showModal();

  return new Promise((done) => {
    resolve = done;
  });
}

// Every way of closing (Cancel, ×, Escape) ends here; a submit has
// already resolved with the input.
function finish(value: ConvertInput | null): void {
  resolve?.(value);
  resolve = null;
}

function handleSubmit(): void {
  if (needsEcosystem.value && !ecosystem.value) {
    return;
  }

  finish({ target: target.value, ecosystem: target.value === "osv" ? ecosystem.value : "" });
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
          Convert {{ source }}
        </h2>

        <button
          type="button"
          class="btn-close"
          aria-label="Close"
          @click="dialog?.close()"
        />
      </div>

      <div class="editor-dialog-body">
        <fieldset class="mb-3">
          <legend class="form-label fs-6">
            Format
          </legend>

          <div class="form-check">
            <input
              id="convert-csaf"
              v-model="target"
              class="form-check-input"
              type="radio"
              value="csaf"
            >
            <label
              class="form-check-label"
              for="convert-csaf"
            >CSAF 2.1 advisory <span class="text-secondary">· for customers of your products</span></label>
          </div>

          <div class="form-check">
            <input
              id="convert-osv"
              v-model="target"
              class="form-check-input"
              type="radio"
              value="osv"
            >
            <label
              class="form-check-label"
              for="convert-osv"
            >OSV 1.9.2 record <span class="text-secondary">· for open-source packages</span></label>
          </div>
        </fieldset>

        <template v-if="target === 'osv'">
          <label
            for="convert-ecosystem"
            class="form-label"
          >
            Ecosystem
            <span
              v-if="needsEcosystem"
              class="text-danger"
            >*</span>
          </label>

          <select
            id="convert-ecosystem"
            v-model="ecosystem"
            class="form-select"
            :required="needsEcosystem"
          >
            <option value="">
              {{ needsEcosystem ? "Choose…" : "Not needed" }}
            </option>
            <option
              v-for="name in ECOSYSTEMS"
              :key="name"
              :value="name"
            >
              {{ name }}
            </option>
          </select>

          <p class="small text-secondary mt-1 mb-2">
            <template v-if="needsEcosystem">
              For {{ productsWithoutPurl.join(", ") }}, which
              {{ productsWithoutPurl.length === 1 ? "has" : "have" }} no package URL.
            </template>
            <template v-else>
              Every product has a package URL, which names its ecosystem.
            </template>
          </p>

          <p class="small text-secondary mb-0">
            The OSV ID stays empty for you to set: OSV IDs start with the
            database's prefix<template v-if="gcveId">, e.g. <code>x_{{ gcveId }}</code>
              (<code>x_</code> marks a database not registered with OSV)</template>.
          </p>
        </template>

        <p class="small text-secondary mt-3 mb-0">
          Creates a new private draft and opens it. This record stays unchanged.
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
            class="btn btn-primary"
          >
            Convert
          </button>
        </div>
      </div>
    </form>
  </dialog>
</template>
