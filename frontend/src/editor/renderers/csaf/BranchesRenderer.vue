<script setup lang="ts">
import {
  computed,
} from "vue";

import type {
  ControlElement,
  JsonSchema,
} from "@jsonforms/core";

import {
  rendererProps,
  useJsonForms,
  useJsonFormsControl,
} from "@jsonforms/vue";

import BranchNode from
  "./BranchNode.vue";

import {
  childCategory,
  nextProductId,
} from "./products";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

/*
 * product_tree.branches: the vendor → product → version tree. See
 * BranchNode.vue for one branch.
 */
const {
  control,
  handleChange,
} = useJsonFormsControl(props);

const jsonforms = useJsonForms();

type Branch = Record<string, unknown>;

const branches = computed(() => {
  return Array.isArray(control.value.data) ? control.value.data as Branch[] : [];
});

const itemSchema = computed(() => control.value.schema.items as JsonSchema);

function change(
  path: string,
  value: unknown,
): void {
  handleChange(path, value);
}

function newProduct(): Branch {
  return { name: "", product_id: nextProductId(jsonforms.core?.data) };
}

function newBranch(
  parentCategory: string | undefined,
): Branch {
  return { category: childCategory(parentCategory), name: "", product: newProduct() };
}

function setBranches(
  next: Branch[],
): void {
  handleChange(control.value.path, next.length ? next : undefined);
}

// Validation messages of one branch itself (not of its product, which
// JSON Forms shows on the product's fields).
function errorsAt(
  path: string,
): string[] {
  const pointer = `/${path.replace(/\./g, "/")}`;
  const own = [pointer, `${pointer}/category`, `${pointer}/name`, `${pointer}/branches`];

  return (jsonforms.core?.errors ?? [])
    .filter((error) => own.includes(error.instancePath))
    .map((error) => `${error.instancePath.slice(pointer.length + 1) || "branch"}: ${error.message}`);
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
        @click="setBranches([...branches, newBranch(undefined)])"
      >
        + Add vendor
      </button>
    </legend>

    <p
      v-if="branches.length === 0"
      class="text-secondary small"
    >
      No branches yet. Branches group products by vendor, product name and version.
    </p>

    <BranchNode
      v-for="(branch, index) in branches"
      :key="`${control.path}.${index}`"
      :branch="branch"
      :path="`${control.path}.${index}`"
      :item-schema="itemSchema"
      :depth="0"
      :enabled="control.enabled"
      :renderers="control.renderers ?? []"
      :cells="control.cells ?? []"
      :change="change"
      :new-branch="newBranch"
      :new-product="newProduct"
      :errors-at="errorsAt"
      @remove="setBranches(branches.filter((_, i) => i !== index))"
    />
  </fieldset>
</template>
