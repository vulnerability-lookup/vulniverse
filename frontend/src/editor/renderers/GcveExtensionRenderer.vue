<script setup lang="ts">
import {
  computed,
  ref,
} from "vue";

import {
  DispatchRenderer,
  rendererProps,
  useJsonFormsArrayControl,
  useJsonFormsControl,
} from "@jsonforms/vue";

import {
  composePaths,
  createDefaultValue,
} from "@jsonforms/core";

import type {
  ControlElement,
  JsonSchema,
  UISchemaElement
} from "@jsonforms/core";

import {
  useCollapsibleItems,
} from "./use-collapsible-items";

import {
  extraGcveEntryFields,
  KNOWN_GCVE_ENTRY_KEYS,
} from "../gcve";

const extensionsSchema = computed((): JsonSchema | undefined => {
  const properties = control.value.schema?.properties;

  if (!properties) {
    return undefined;
  }

  return properties.extensions;
});

const registeredExtensionIds = computed((): string[] => {
  return Object.keys(
    extensionsSchema.value?.properties ?? {},
  );
});

function extensionsOf(
  index: number,
): Record<string, unknown> {
  return items.value[index]?.extensions ?? {};
}

function presentRegisteredExtensions(
  index: number,
): string[] {
  const current = extensionsOf(index);

  return registeredExtensionIds.value.filter(
    (id) => Object.prototype.hasOwnProperty.call(current, id),
  );
}

function availableExtensions(
  index: number,
): string[] {
  const current = extensionsOf(index);

  return registeredExtensionIds.value.filter(
    (id) => !Object.prototype.hasOwnProperty.call(current, id),
  );
}

const selectedExtension = ref<Record<number, string>>({});

/*
 * Per-extension fold state, keyed by "entryIndex:extensionId" (a
 * GCVE entry can have more than one registered extension, and a
 * document can have more than one entry). Same collapsed-by-default
 * idea as useCollapsibleItems() above, kept as its own Set rather than
 * reusing that composable since this collapses by extensionId within
 * an entry, not by array index — a freshly-added extension (see
 * addExtension below) is explicitly expanded so its fields are visible
 * immediately; everything else (including one just loaded from a
 * pasted record) starts collapsed to keep a multi-extension entry
 * scannable, and only expands on request.
 */
const expandedExtensions = ref<Set<string>>(new Set());

function extensionKey(
  index: number,
  extensionId: string,
): string {
  return `${index}:${extensionId}`;
}

function isExtensionExpanded(
  index: number,
  extensionId: string,
): boolean {
  return expandedExtensions.value.has(
    extensionKey(index, extensionId),
  );
}

function toggleExtension(
  index: number,
  extensionId: string,
): void {
  const key = extensionKey(index, extensionId);

  if (expandedExtensions.value.has(key)) {
    expandedExtensions.value.delete(key);
  } else {
    expandedExtensions.value.add(key);
  }
}

function extensionSchema(
  extensionId: string,
): JsonSchema | undefined {
  return extensionsSchema.value?.properties?.[extensionId];
}

function addExtension(
  index: number,
): void {
  const extensionId = selectedExtension.value[index];

  if (!extensionId) {
    return;
  }

  const schema = extensionSchema(extensionId);

  if (!schema) {
    return;
  }

  const current = extensionsOf(index);

  handleChange(
    composePaths(
      itemPath(index),
      "extensions",
    ),
    {
      ...current,

      [extensionId]: createDefaultValue(
        schema,
        control.value.rootSchema,
      ),
    },
  );

  expandedExtensions.value.add(extensionKey(index, extensionId));

  selectedExtension.value[index] = "";
}

function removeExtension(
  index: number,
  extensionId: string,
): void {
  const updated = {
    ...extensionsOf(index),
  };

  delete updated[extensionId];

  handleChange(
    composePaths(
      itemPath(index),
      "extensions",
    ),
    Object.keys(updated).length > 0
      ? updated
      : undefined,
  );
}


function uiSchemaForExtension(
  extensionId: string,
): UISchemaElement {
  const schema = extensionSchema(extensionId);

  const properties = schema?.properties ?? {};

  return {
    type: "VerticalLayout",
    elements: Object.keys(properties).map((key) => ({
      type: "Control",
      scope: `#/properties/${key}`,
      // A nested array reached from here (e.g. ai_annotations[])
      // dispatches to ArrayCardRenderer, which reads this to know
      // it's already one level deep — see that component's own
      // depth/cardBackgroundClass — since this content sits inside
      // the extension card below, itself one level inside the GCVE
      // entry card.
      options: { depth: 1 },
    })),
  };
}


function unknownExtensions(
  index: number,
): Record<string, unknown> {
  const registered = new Set(
    registeredExtensionIds.value,
  );

  return Object.fromEntries(
    Object.entries(
      extensionsOf(index),
    ).filter(
      ([id]) => !registered.has(id),
    ),
  );
}


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
  extensions?: Record<string, unknown>;
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

/*
 * Anything on an entry beyond the four known fields
 * has no dedicated control — the schema itself gives
 * it no name/type/shape to build one from (see
 * gcve-bcp-05.schema.json's additionalProperties: true). Edited as
 * raw JSON instead: one entry can be open for editing at a time,
 * tracked by index rather than trying to keep N independent drafts
 * in sync with upstream data changes.
 */
const editingExtraFieldsIndex = ref<number | null>(null);
const extraFieldsDraft = ref("");
const extraFieldsError = ref<string | null>(null);

function extraFieldsOf(
  index: number,
): Record<string, unknown> {
  const extra = extraGcveEntryFields(
    (items.value[index] ?? {}) as Record<string, unknown>,
  );

  // "extensions" is excluded from the generic extra-fields bag (see
  // KNOWN_GCVE_ENTRY_KEYS) since recognized sub-keys get their own
  // dedicated UI above — but an *unrecognized* sub-key (not yet in
  // schemas/extensions/gcve/registry.json) has nowhere else to go, so
  // it still needs to surface here, or it becomes invisible/
  // uneditable even though the underlying data is preserved.
  const unknown = unknownExtensions(index);

  return Object.keys(unknown).length > 0
    ? { ...extra, extensions: unknown }
    : extra;
}

function hasExtraFields(
  index: number,
): boolean {
  return Object.keys(extraFieldsOf(index)).length > 0;
}

function formattedExtraFields(
  index: number,
): string {
  return JSON.stringify(
    extraFieldsOf(index),
    null,
    2,
  );
}

function startEditingExtraFields(
  index: number,
): void {
  editingExtraFieldsIndex.value = index;
  extraFieldsDraft.value = formattedExtraFields(index);
  extraFieldsError.value = null;
}

function cancelEditingExtraFields(): void {
  editingExtraFieldsIndex.value = null;
  extraFieldsError.value = null;
}

function applyExtraFields(
  index: number,
): void {
  let parsed: unknown;

  try {
    parsed = JSON.parse(extraFieldsDraft.value);
  } catch {
    extraFieldsError.value = "Invalid JSON.";
    return;
  }

  if (
    typeof parsed !== "object"
    || parsed === null
    || Array.isArray(parsed)
  ) {
    extraFieldsError.value = "Must be a JSON object.";
    return;
  }

  // The four known fields (plus "extensions" as a whole) stay under
  // their own dedicated controls — this box only ever contributes the
  // keys it's shown, even if the user pastes one of those names in
  // too. "extensions" is handled separately below: this box only
  // owns the *unrecognized* sub-keys within it, so a registered
  // extension edited via the dedicated UI above must never be
  // clobbered by whatever this box last had loaded.
  const current = (items.value[index] ?? {}) as Record<string, unknown>;

  const knownFields = Object.fromEntries(
    Object.entries(current).filter(
      ([key]) => KNOWN_GCVE_ENTRY_KEYS.has(key) && key !== "extensions",
    ),
  );

  const parsedObject = parsed as Record<string, unknown>;

  const extraFields = Object.fromEntries(
    Object.entries(parsedObject).filter(
      ([key]) => !KNOWN_GCVE_ENTRY_KEYS.has(key),
    ),
  );

  const registeredExtensions = Object.fromEntries(
    Object.entries(extensionsOf(index)).filter(
      ([id]) => registeredExtensionIds.value.includes(id),
    ),
  );

  const parsedExtensions = parsedObject.extensions;

  const editedUnknownExtensions =
    parsedExtensions
    && typeof parsedExtensions === "object"
    && !Array.isArray(parsedExtensions)
      ? (parsedExtensions as Record<string, unknown>)
      : {};

  const mergedExtensions = {
    ...registeredExtensions,
    ...editedUnknownExtensions,
  };

  handleChange(
    itemPath(index),
    {
      ...knownFields,
      ...extraFields,
      ...(Object.keys(mergedExtensions).length > 0
        ? { extensions: mergedExtensions }
        : {}),
    },
  );

  editingExtraFieldsIndex.value = null;
  extraFieldsError.value = null;
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


        <div class="mt-4">
          <div
            class="d-flex align-items-center justify-content-between mb-2"
          >
            <label class="form-label fw-semibold mb-0">
              Extensions
            </label>
          </div>

          <p
            v-if="presentRegisteredExtensions(index).length === 0"
            class="text-secondary small"
          >
            No registered GCVE extensions.
          </p>

          <div
            v-for="extensionId in presentRegisteredExtensions(index)"
            :key="extensionId"
            class="card mb-3"
          >
            <div
              class="card-header d-flex align-items-center justify-content-between"
            >
              <span class="fw-semibold">
                {{ extensionId.toUpperCase() }}
              </span>

              <div class="d-flex gap-1">
                <button
                  type="button"
                  class="btn btn-outline-secondary btn-sm"
                  @click="toggleExtension(index, extensionId)"
                >
                  {{ isExtensionExpanded(index, extensionId) ? "▾" : "▸" }}
                </button>

                <button
                  type="button"
                  class="btn btn-outline-danger btn-sm"
                  :disabled="!control.enabled"
                  @click="removeExtension(index, extensionId)"
                >
                  Remove
                </button>
              </div>
            </div>

            <div
              v-if="isExtensionExpanded(index, extensionId)"
              class="card-body"
            >
              <dispatch-renderer
                v-if="extensionSchema(extensionId)"
                :schema="extensionSchema(extensionId)!"
                :uischema="uiSchemaForExtension(extensionId)"
                :path="
                  composePaths(
                    composePaths(itemPath(index), 'extensions'),
                    extensionId
                  )
                "
                :enabled="control.enabled"
                :renderers="control.renderers"
                :cells="control.cells"
              />
            </div>
          </div>

          <div
            v-if="availableExtensions(index).length > 0"
            class="d-flex gap-2"
          >
            <select
              v-model="selectedExtension[index]"
              class="form-select form-select-sm"
              :disabled="!control.enabled"
            >
              <option value="">
                Select extension…
              </option>

              <option
                v-for="extensionId in availableExtensions(index)"
                :key="extensionId"
                :value="extensionId"
              >
                {{ extensionId.toUpperCase() }}
              </option>
            </select>

            <button
              type="button"
              class="btn btn-outline-primary btn-sm text-nowrap"
              :disabled="
                !control.enabled
                || !selectedExtension[index]
              "
              @click="addExtension(index)"
            >
              + Add extension
            </button>
          </div>
        </div>

        <div class="mt-3">
          <label class="form-label d-flex align-items-center justify-content-between">
            Extra fields (JSON)

            <button
              v-if="editingExtraFieldsIndex !== index"
              type="button"
              class="btn btn-outline-secondary btn-sm"
              :disabled="!control.enabled"
              @click="startEditingExtraFields(index)"
            >
              {{ hasExtraFields(index) ? "Edit" : "+ Add extra fields" }}
            </button>
          </label>

          <template v-if="editingExtraFieldsIndex === index">
            <textarea
              v-model="extraFieldsDraft"
              class="form-control font-monospace small"
              rows="8"
              spellcheck="false"
            />

            <p
              v-if="extraFieldsError"
              role="alert"
              class="text-danger small mt-1 mb-0"
            >
              {{ extraFieldsError }}
            </p>

            <div class="d-flex justify-content-end gap-2 mt-2">
              <button
                type="button"
                class="btn btn-outline-secondary btn-sm"
                @click="cancelEditingExtraFields"
              >
                Cancel
              </button>

              <button
                type="button"
                class="btn btn-primary btn-sm"
                @click="applyExtraFields(index)"
              >
                Apply
              </button>
            </div>
          </template>

          <template v-else>
            <p
              v-if="!hasExtraFields(index)"
              class="text-secondary small mb-0"
            >
              No extra fields.
            </p>

            <pre
              v-else
              class="extra-fields-preview small mb-0"
            >{{ formattedExtraFields(index) }}</pre>
          </template>
        </div>
      </div>
    </div>
  </fieldset>
</template>

<style scoped>
.extra-fields-preview {
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 20rem;
  overflow-y: auto;
}
</style>
