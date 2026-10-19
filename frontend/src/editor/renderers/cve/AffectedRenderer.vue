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
} from "../common/use-collapsible-items";

import {
  CpeAutocompleteField,
} from "../../cpe";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

const {
  control,
  addItem,
  removeItems,
} = useJsonFormsArrayControl(props);

/*
 * Only needed for the vendor/product fields' live-search autocomplete
 * below (CpeAutocompleteField), which write directly via handleChange
 * + composePaths rather than through DispatchRenderer like every
 * other field in this renderer — the same handleChange-on-the-side
 * pattern GcveExtensionRenderer.vue uses for its own nested writes.
 */
const { handleChange } = useJsonFormsControl(props);

const items = computed(() => {
  return (control.value.data ?? []) as Array<
    Record<string, unknown>
  >;
});

const { isExpanded, toggle } = useCollapsibleItems(
  computed(() => items.value.length),
);

/*
 * @jsonforms/core's Generate.uiSchema (used by the vanilla
 * ObjectRenderer whenever an array item has no explicit uischema)
 * crashes with "Maximum call stack size exceeded" once the item
 * schema has enough properties — confirmed by bisection, and
 * "affected" has 13. Dispatching each field through its own
 * explicit Control (below) instead of one auto-generated Group
 * avoids that path entirely; the fields themselves still go
 * through the normal String/Enum/Array renderers, unchanged.
 */
/*
 * "vendor" and "product" are rendered separately below via
 * CpeAutocompleteField (a live-search autocomplete), not through
 * dispatch-renderer like every other field here.
 */
function fieldPath(
  index: number,
  key: string,
): string {
  return composePaths(
    itemPath(index),
    key,
  );
}

function onVendorUpdate(
  index: number,
  value: string,
): void {
  handleChange(
    fieldPath(index, "vendor"),
    value || undefined,
  );
}

function onProductUpdate(
  index: number,
  value: string,
): void {
  handleChange(
    fieldPath(index, "product"),
    value || undefined,
  );
}

const detailFields = [
  "packageName",
  "packageURL",
  "collectionURL",
  "repo",
  "defaultStatus",
];

const listFields = [
  "cpes",
  "modules",
  "programFiles",
  "programRoutines",
  "platforms",
];

function controlFor(
  key: string,
): ControlElement {
  return {
    type: "Control",
    scope: `#/properties/${key}`,
  };
}

function itemPath(
  index: number,
): string {
  return composePaths(
    control.value.path,
    `${index}`,
  );
}

function addAffected(): void {
  addItem(
    control.value.path,
    {},
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
        @click="addAffected"
      >
        + Add affected product
      </button>
    </legend>

    <p
      v-if="items.length === 0"
      class="text-secondary"
    >
      No affected products yet.
    </p>

    <div
      v-for="(item, index) in items"
      :key="`${control.path}-${index}`"
      class="card mb-3"
    >
      <div class="card-header d-flex justify-content-between align-items-center">
        <span class="fw-semibold">
          {{
            item.vendor || item.product
              ? `${item.vendor ?? "?"} — ${item.product ?? "?"}`
              : `Affected product ${index + 1}`
          }}
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
            <label
              :for="`${control.id}-${index}-vendor`"
              class="form-label"
            >
              Vendor
            </label>

            <CpeAutocompleteField
              :id="`${control.id}-${index}-vendor`"
              :model-value="(item.vendor as string) ?? ''"
              method="searchCpeVendors"
              kind="vendor"
              input-class="form-control"
              :disabled="!control.enabled"
              @update:model-value="(value) => onVendorUpdate(index, value)"
            />
          </div>

          <div class="col-md-6">
            <label
              :for="`${control.id}-${index}-product`"
              class="form-label"
            >
              Product
            </label>

            <CpeAutocompleteField
              :id="`${control.id}-${index}-product`"
              :model-value="(item.product as string) ?? ''"
              method="searchCpeProducts"
              kind="product"
              input-class="form-control"
              :disabled="!control.enabled"
              @update:model-value="(value) => onProductUpdate(index, value)"
            />
          </div>
        </div>

        <div class="row g-3 mb-3">
          <div
            v-for="key in detailFields"
            :key="key"
            class="col-md-4"
          >
            <dispatch-renderer
              :schema="control.schema"
              :uischema="controlFor(key)"
              :path="itemPath(index)"
              :enabled="control.enabled"
              :renderers="control.renderers"
              :cells="control.cells"
            />
          </div>
        </div>

        <div
          v-for="key in listFields"
          :key="key"
          class="mb-3"
        >
          <dispatch-renderer
            :schema="control.schema"
            :uischema="controlFor(key)"
            :path="itemPath(index)"
            :enabled="control.enabled"
            :renderers="control.renderers"
            :cells="control.cells"
          />
        </div>

        <dispatch-renderer
          :schema="control.schema"
          :uischema="controlFor('versions')"
          :path="itemPath(index)"
          :enabled="control.enabled"
          :renderers="control.renderers"
          :cells="control.cells"
        />
      </div>
    </div>
  </fieldset>
</template>
