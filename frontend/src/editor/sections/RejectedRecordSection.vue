<script setup lang="ts">
import {
  computed,
} from "vue";

import type {
  Description,
} from "../contracts";

import {
  useEditorContext,
} from "../use-editor-context";

/*
 * A rejected record's containers.cna is a different, minimal shape
 * from the normal one (schemas/upstream/cve/5.2.0's
 * cnaRejectedContainer: additionalProperties false, only
 * providerMetadata/rejectedReasons/replacedBy) — the generated
 * schema-driven form (SchemaFormSection) is built entirely around
 * the normal shape's fields (descriptions/affected/references/...),
 * none of which apply here. VulniverseEditor.ce.vue swaps to this
 * section for the "Editor" tab specifically when the record is
 * rejected, instead of extending the generator for a shape this
 * different and this small.
 */
const editor = useEditorContext();

const cna = computed(() => {
  editor.record.value ??= {};
  editor.record.value.containers ??= {};
  editor.record.value.containers.cna ??= {};

  return editor.record.value.containers.cna;
});

const providerMetadata = computed(() => {
  cna.value.providerMetadata ??= {};

  return cna.value.providerMetadata;
});

const reasons = computed<Description[]>(() => {
  cna.value.rejectedReasons ??= [];

  return cna.value.rejectedReasons;
});

function addReason(): void {
  reasons.value.push({
    lang: "en",
    value: "",
  });
}

function removeReason(
  index: number,
): void {
  reasons.value.splice(index, 1);
}

/*
 * Unlike rejectedReasons (required — always seeded by the reject
 * dialog before this section can ever render), replacedBy is
 * optional and has its own minItems: 1 — so, unlike `reasons` above,
 * this must NOT eagerly create the array just because the template
 * reads it every render. Doing that would silently persist a
 * `replacedBy: []` into the saved record the moment this tab is
 * merely viewed, which is itself schema-invalid.
 */
const replacedBy = computed<string[]>(() => {
  return cna.value.replacedBy ?? [];
});

function addReplacedBy(): void {
  cna.value.replacedBy ??= [];
  cna.value.replacedBy.push("");
}

function removeReplacedBy(
  index: number,
): void {
  cna.value.replacedBy?.splice(index, 1);

  if (cna.value.replacedBy?.length === 0) {
    delete cna.value.replacedBy;
  }
}
</script>

<template>
  <div class="p-2">
    <div
      class="alert alert-secondary"
      role="status"
    >
      This record is marked <strong>REJECTED</strong>. A rejected CVE
      Record only carries a rejection reason (and optionally which
      ID(s) replaced it) — not the usual descriptions/affected-
      products/references fields, which is why this tab looks
      different from a normal record.
    </div>

    <section class="mb-4">
      <h2 class="h5">
        Rejection reasons
        <span class="text-danger">*</span>
      </h2>

      <div
        v-for="(reason, index) in reasons"
        :key="index"
        class="card mb-2"
      >
        <div class="card-body">
          <div class="row g-2">
            <div class="col-2">
              <label class="form-label">Lang</label>

              <input
                v-model="reason.lang"
                type="text"
                class="form-control"
                placeholder="en"
              >
            </div>

            <div class="col">
              <label class="form-label">Reason</label>

              <textarea
                v-model="reason.value"
                class="form-control"
                rows="2"
              />
            </div>

            <div class="col-auto d-flex align-items-end">
              <button
                type="button"
                class="btn btn-outline-danger btn-sm"
                :disabled="reasons.length <= 1"
                :title="
                  reasons.length <= 1
                    ? 'At least one rejection reason is required'
                    : undefined
                "
                @click="removeReason(index)"
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      </div>

      <button
        type="button"
        class="btn btn-outline-secondary btn-sm"
        @click="addReason"
      >
        Add reason
      </button>
    </section>

    <section class="mb-4">
      <h2 class="h5">
        Replaced by
      </h2>

      <p class="text-secondary small">
        CVE/GCVE IDs this one was rejected in favor of, if any.
      </p>

      <div
        v-for="(_id, index) in replacedBy"
        :key="index"
        class="input-group mb-2"
      >
        <input
          v-model="replacedBy[index]"
          type="text"
          class="form-control"
          placeholder="CVE-2026-00001"
        >

        <button
          type="button"
          class="btn btn-outline-danger"
          @click="removeReplacedBy(index)"
        >
          Remove
        </button>
      </div>

      <button
        type="button"
        class="btn btn-outline-secondary btn-sm"
        @click="addReplacedBy"
      >
        Add ID
      </button>
    </section>

    <section>
      <h2 class="h5">
        Provider metadata
      </h2>

      <div class="row g-2">
        <div class="col">
          <label class="form-label">Org ID</label>

          <input
            v-model="providerMetadata.orgId"
            type="text"
            class="form-control"
          >
        </div>

        <div class="col">
          <label class="form-label">Short name</label>

          <input
            v-model="providerMetadata.shortName"
            type="text"
            class="form-control"
          >
        </div>
      </div>
    </section>
  </div>
</template>
