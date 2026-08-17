<script setup lang="ts">
import {
  computed,
} from "vue";

import {
  DispatchRenderer,
  rendererProps,
  useJsonFormsArrayControl,
  useJsonFormsControl,
} from "@jsonforms/vue";

import {
  composePaths,
} from "@jsonforms/core";

import type {
  ControlElement,
} from "@jsonforms/core";

import {
  useCollapsibleItems,
} from "./use-collapsible-items";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

const {
  control,
  addItem,
  removeItems,
} = useJsonFormsArrayControl(props);

/*
 * Neither vulnId nor recordType is a fixed enum in the schema
 * (GCVE-BCP-05 explicitly allows unknown recordType values and
 * relationship types forward-compatibly), so useJsonFormsControl's
 * handleChange — not addItem/removeItems' fixed operations — drives
 * recordType presets and the relationships sub-list below.
 */
const { handleChange } = useJsonFormsControl(props);

interface GcveExtensionItem {
  vulnId?: string;
  recordType?: string;
  relationships?: Array<{
    destId?: string;
    type?: string;
    srcId?: string;
  }>;
  language?: string;
}

const items = computed(() => {
  return (control.value.data ?? []) as GcveExtensionItem[];
});

const { isExpanded, toggle } = useCollapsibleItems(
  computed(() => items.value.length),
);

// recordType values GCVE-BCP-05 names explicitly. Shown as one-
// click presets, not a hard enum — unknown values are still valid.
const RECORD_TYPE_PRESETS = [
  "creation",
  "update",
  "analysis",
  "metadata",
  "reference",
  "comment",
  "statement",
  "remediation",
  "deprecation",
  "detection",
  "translation",
];

// BCP-05's recommended VXREF-derived relationship types, mirroring
// backend/.../record_validation.py's RECOMMENDED_RELATIONSHIP_TYPES
// — unknown values are allowed but the backend warns about them.
const RELATIONSHIP_TYPE_PRESETS = [
  "possibly_related",
  "related",
  "not equal",
  "equal",
  "superset",
  "subset",
  "overlap",
  "opposes",
  "not_applicable",
];

function itemPath(
  index: number,
): string {
  return composePaths(
    control.value.path,
    `${index}`,
  );
}

function controlFor(
  key: string,
): ControlElement {
  return {
    type: "Control",
    scope: `#/properties/${key}`,
  };
}

function labelFor(
  index: number,
): string {
  const item = items.value[index];

  return item?.vulnId
    || item?.recordType
    || `GCVE entry ${index + 1}`;
}

function setRecordType(
  index: number,
  value: string,
): void {
  handleChange(
    composePaths(itemPath(index), "recordType"),
    value,
  );
}

function relationshipsOf(
  index: number,
) {
  return items.value[index]?.relationships ?? [];
}

function setRelationships(
  index: number,
  relationships: GcveExtensionItem["relationships"],
): void {
  handleChange(
    composePaths(itemPath(index), "relationships"),
    relationships,
  );
}

function addRelationship(
  index: number,
): void {
  setRelationships(index, [
    ...relationshipsOf(index),
    { destId: "", type: "" },
  ]);
}

function updateRelationship(
  index: number,
  relationshipIndex: number,
  key: "destId" | "type" | "srcId",
  value: string,
): void {
  setRelationships(
    index,
    relationshipsOf(index).map((relationship, currentIndex) =>
      currentIndex === relationshipIndex
        ? { ...relationship, [key]: value }
        : relationship,
    ),
  );
}

function removeRelationship(
  index: number,
  relationshipIndex: number,
): void {
  setRelationships(
    index,
    relationshipsOf(index).filter(
      (_, currentIndex) => currentIndex !== relationshipIndex,
    ),
  );
}

function addEntry(): void {
  addItem(
    control.value.path,
    { vulnId: "", recordType: "" },
  )?.();
}
</script>

<template>
  <fieldset
    v-if="control.visible"
    class="mb-3"
  >
    <legend class="d-flex align-items-center justify-content-between h5">
      {{ control.label }}

      <button
        type="button"
        class="btn btn-primary btn-sm"
        :disabled="!control.enabled"
        @click="addEntry"
      >
        + Add GCVE entry
      </button>
    </legend>

    <p
      v-if="items.length === 0"
      class="text-secondary"
    >
      No GCVE extension entries yet.
    </p>

    <div
      v-for="(item, index) in items"
      :key="`${control.path}-${index}`"
      class="card mb-3"
    >
      <div class="card-header d-flex justify-content-between align-items-center">
        <span class="fw-semibold">{{ labelFor(index) }}</span>

        <div class="d-flex gap-1">
          <button
            type="button"
            class="btn btn-outline-secondary btn-sm"
            @click="toggle(index)"
          >
            {{ isExpanded(index) ? "▾" : "▸" }}
          </button>

          <button
            type="button"
            class="btn btn-outline-danger btn-sm"
            :disabled="!control.enabled"
            @click="removeItems?.(control.path, [index])?.()"
          >
            Remove
          </button>
        </div>
      </div>

      <div
        v-if="isExpanded(index)"
        class="card-body"
      >
        <div class="row g-3 mb-3">
          <div class="col-md-6">
            <dispatch-renderer
              :schema="control.schema"
              :uischema="controlFor('vulnId')"
              :path="itemPath(index)"
              :enabled="control.enabled"
              :renderers="control.renderers"
              :cells="control.cells"
            />
          </div>

          <div class="col-md-6">
            <label class="form-label">Record type</label>

            <input
              :list="`gcve-record-type-${index}`"
              type="text"
              class="form-control"
              :value="item.recordType ?? ''"
              :disabled="!control.enabled"
              @change="
                setRecordType(
                  index,
                  ($event.target as HTMLInputElement).value,
                )
              "
            >

            <datalist :id="`gcve-record-type-${index}`">
              <option
                v-for="preset in RECORD_TYPE_PRESETS"
                :key="preset"
                :value="preset"
              />
            </datalist>
          </div>
        </div>

        <div class="mb-3">
          <dispatch-renderer
            :schema="control.schema"
            :uischema="controlFor('language')"
            :path="itemPath(index)"
            :enabled="control.enabled"
            :renderers="control.renderers"
            :cells="control.cells"
          />
        </div>

        <label class="form-label d-flex align-items-center justify-content-between">
          Relationships

          <button
            type="button"
            class="btn btn-outline-secondary btn-sm"
            :disabled="!control.enabled"
            @click="addRelationship(index)"
          >
            + Add relationship
          </button>
        </label>

        <p
          v-if="relationshipsOf(index).length === 0"
          class="text-secondary small"
        >
          No relationships yet.
        </p>

        <div
          v-for="(relationship, relationshipIndex) in relationshipsOf(index)"
          :key="relationshipIndex"
          class="row g-2 mb-2 align-items-end"
        >
          <div class="col-md-4">
            <label class="form-label small">Destination ID</label>

            <input
              type="text"
              class="form-control form-control-sm"
              :value="relationship.destId ?? ''"
              :disabled="!control.enabled"
              @change="
                updateRelationship(
                  index,
                  relationshipIndex,
                  'destId',
                  ($event.target as HTMLInputElement).value,
                )
              "
            >
          </div>

          <div class="col-md-4">
            <label class="form-label small">Type</label>

            <input
              :list="`gcve-relationship-type-${index}-${relationshipIndex}`"
              type="text"
              class="form-control form-control-sm"
              :value="relationship.type ?? ''"
              :disabled="!control.enabled"
              @change="
                updateRelationship(
                  index,
                  relationshipIndex,
                  'type',
                  ($event.target as HTMLInputElement).value,
                )
              "
            >

            <datalist :id="`gcve-relationship-type-${index}-${relationshipIndex}`">
              <option
                v-for="preset in RELATIONSHIP_TYPE_PRESETS"
                :key="preset"
                :value="preset"
              />
            </datalist>
          </div>

          <div class="col-md-3">
            <label class="form-label small">Source ID (optional)</label>

            <input
              type="text"
              class="form-control form-control-sm"
              :value="relationship.srcId ?? ''"
              :disabled="!control.enabled"
              @change="
                updateRelationship(
                  index,
                  relationshipIndex,
                  'srcId',
                  ($event.target as HTMLInputElement).value,
                )
              "
            >
          </div>

          <div class="col-md-1">
            <button
              type="button"
              class="btn btn-outline-danger btn-sm"
              :disabled="!control.enabled"
              @click="removeRelationship(index, relationshipIndex)"
            >
              ✕
            </button>
          </div>
        </div>
      </div>
    </div>
  </fieldset>
</template>
