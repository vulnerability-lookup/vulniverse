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
  createDefaultValue,
  getFirstPrimitiveProp,
} from "@jsonforms/core";

import type {
  ControlElement,
  JsonSchema,
  UISchemaElement,
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
 * removeItems only ever splices the array. For a property that's
 * required on its parent, disabling delete at schema.minItems
 * (below) is correct — there's no valid fallback. But for an
 * optional property (control.required, already computed by
 * JSONForms itself), splicing down below minItems leaves a
 * permanently invalid AND — in the vanilla renderer — permanently
 * undeletable state. handleChange lets us clear the whole property
 * instead, which is what "optional, but non-empty if present"
 * actually means once you want zero entries.
 */
const { handleChange } = useJsonFormsControl(props);

const items = computed(() => {
  return (control.value.data ?? []) as unknown[];
});

const isObjectItems = computed(() => {
  return control.value.schema?.type === "object";
});

const atMinItems = computed(() => {
  const minItems = control.value.arraySchema?.minItems ?? 0;

  return items.value.length <= minItems;
});

/*
 * A property shaped like {type: "array", items: {oneOf: [...]}} is
 * how every "tags" field in the CVE schema is defined (a free
 * "x_"-prefixed extension string, or one of a small fixed enum) —
 * confirmed to be exactly 3 occurrences in the whole schema
 * (reference.tags, cnaPublishedContainer.tags, adpContainer.tags),
 * all the same concept. Flattening it as a plain Control would fall
 * through to JSONForms' generic oneOf picker (confusing "oneOf-0"/
 * "oneOf-1" labels); routing it to TagsRenderer instead works no
 * matter how deeply this property is nested — e.g.
 * problemTypes[].descriptions[].references[].tags, reached only by
 * this renderer flattening itself recursively — since TagsRenderer
 * derives its known values straight from this same schema shape
 * rather than needing a per-path config entry.
 */
function isTagsShaped(
  propertySchema: JsonSchema | undefined,
): boolean {
  const schema = propertySchema as Record<string, unknown> | undefined;

  if (!schema || schema.type !== "array") {
    return false;
  }

  const items = schema.items;

  return (
    !!items
    && typeof items === "object"
    && Array.isArray((items as Record<string, unknown>).oneOf)
  );
}

/*
 * @jsonforms/core's Generate.uiSchema — what findUISchema falls
 * back to for an array item with no explicit uischema — is what
 * crashed on "affected" (13 properties) and, confirmed by testing,
 * crashes the same way on anything else with enough properties
 * (containers.adp's 19). AffectedRenderer avoided it by hand-
 * building a flat list of Controls instead of asking JSONForms to
 * auto-generate one; this does the same thing generically for any
 * object-item array, so no array can hit that path again — the
 * fields themselves still go through the normal String/Enum/Array
 * renderers, unchanged. For a primitive item (string/number/
 * boolean array, e.g. cpes/modules/platforms) there are no
 * properties to flatten — scope "#" dispatches straight at the
 * item value itself.
 */
const childUiSchema = computed((): UISchemaElement => {
  if (!isObjectItems.value) {
    return {
      type: "Control",
      scope: "#",
    } as ControlElement;
  }

  const properties = control.value.schema?.properties ?? {};

  return {
    type: "VerticalLayout",
    elements: Object.keys(properties).map((key) => ({
      type: "Control",
      scope: `#/properties/${key}`,
      ...(isTagsShaped(properties[key])
        ? { options: { renderer: "vulniverse-tags" } }
        : {}),
    })),
  };
});

const { isExpanded, toggle } = useCollapsibleItems(
  computed(() => items.value.length),
);

function labelFor(
  index: number,
): string {
  const item = items.value[index];

  if (typeof item === "string" && item.length > 0) {
    return item;
  }

  if (typeof item === "number" || typeof item === "boolean") {
    return String(item);
  }

  const labelProperty = isObjectItems.value
    ? getFirstPrimitiveProp(control.value.schema)
    : undefined;

  const value = labelProperty && item && typeof item === "object"
    ? (item as Record<string, unknown>)[labelProperty]
    : undefined;

  return typeof value === "string" && value.length > 0
    ? value
    : `Item ${index + 1}`;
}

function itemPath(
  index: number,
): string {
  return composePaths(
    control.value.path,
    `${index}`,
  );
}

function addEntry(): void {
  addItem(
    control.value.path,
    createDefaultValue(
      control.value.schema,
      control.value.rootSchema,
    ),
  )?.();
}

function deleteEntry(
  index: number,
): void {
  if (atMinItems.value) {
    if (control.value.required) {
      return;
    }

    handleChange(
      control.value.path,
      undefined,
    );

    return;
  }

  removeItems?.(control.value.path, [index])?.();
}
</script>

<template>
  <fieldset
    v-if="control.visible"
    class="mb-3"
  >
    <legend class="d-flex align-items-center justify-content-between h6">
      {{ control.label }}

      <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        :disabled="!control.enabled"
        @click="addEntry"
      >
        + Add
      </button>
    </legend>

    <p
      v-if="items.length === 0"
      class="text-secondary small"
    >
      No data
    </p>

    <div
      v-for="(item, index) in items"
      :key="`${control.path}-${index}`"
      class="card mb-2"
    >
      <div class="card-header d-flex justify-content-between align-items-center py-2">
        <span class="fw-semibold small">
          {{ labelFor(index) }}
        </span>

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
            :disabled="!control.enabled || (control.required && atMinItems)"
            @click="deleteEntry(index)"
          >
            Remove
          </button>
        </div>
      </div>

      <div
        v-if="isExpanded(index)"
        class="card-body"
      >
        <dispatch-renderer
          :schema="control.schema"
          :uischema="childUiSchema"
          :path="itemPath(index)"
          :enabled="control.enabled"
          :renderers="control.renderers"
          :cells="control.cells"
        />
      </div>
    </div>
  </fieldset>
</template>
