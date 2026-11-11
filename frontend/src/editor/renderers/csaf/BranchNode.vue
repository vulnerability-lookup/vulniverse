<script setup lang="ts">
import {
  computed,
} from "vue";

import {
  DispatchRenderer,
} from "@jsonforms/vue";

import type {
  JsonFormsCellRendererRegistryEntry,
  JsonFormsRendererRegistryEntry,
  JsonSchema,
} from "@jsonforms/core";

import {
  childCategory,
} from "./products";

type Branch = Record<string, unknown>;

/*
 * One branch of the product tree: a category and name, holding either
 * sub-branches or a product (CSAF allows exactly one of them). The
 * branches are drawn here, recursively; JSON Forms would render the
 * recursive schema without end. The product is left to JSON Forms.
 */
const props = defineProps<{
  branch: Branch;
  path: string;
  // The schema of one branch, the same at every depth.
  itemSchema: JsonSchema;
  depth: number;
  enabled: boolean;
  renderers: JsonFormsRendererRegistryEntry[];
  cells: JsonFormsCellRendererRegistryEntry[];
  change: (path: string, value: unknown) => void;
  newBranch: (parentCategory: string | undefined) => Branch;
  newProduct: () => Branch;
  errorsAt: (path: string) => string[];
}>();

const emit = defineEmits<{
  remove: [];
}>();

const categories = computed(() => {
  const values = props.itemSchema.properties?.category?.enum;

  return Array.isArray(values) ? values.map(String) : [];
});

const category = computed(() => (typeof props.branch.category === "string" ? props.branch.category : ""));
const name = computed(() => (typeof props.branch.name === "string" ? props.branch.name : ""));

const children = computed(() => {
  return Array.isArray(props.branch.branches) ? props.branch.branches as Branch[] : [];
});

const holdsProduct = computed(() => "product" in props.branch);

const errors = computed(() => props.errorsAt(props.path));

function label(
  value: string,
): string {
  return value.replace(/_/g, " ");
}

function setField(
  key: "category" | "name",
  value: string,
): void {
  props.change(`${props.path}.${key}`, value);
}

// Product or sub-branches: one replaces the other.
function setHolds(
  product: boolean,
): void {
  props.change(props.path, {
    category: category.value,
    name: name.value,
    ...(product
      ? { product: props.newProduct() }
      : { branches: [props.newBranch(category.value)] }),
  });
}

function setChildren(
  next: Branch[],
): void {
  // An empty list is unset; the branch then shows its error until it
  // gets a product or a new sub-branch.
  props.change(`${props.path}.branches`, next.length ? next : undefined);
}
</script>

<template>
  <details
    class="card mb-2"
    :open="depth < 2"
  >
    <summary class="card-header d-flex align-items-center gap-2">
      <span class="badge text-bg-light border">{{ label(category) || "branch" }}</span>
      <span class="fw-semibold">{{ name || "(no name)" }}</span>
      <span
        v-if="errors.length"
        class="badge text-bg-danger"
      >{{ errors.length }} error{{ errors.length === 1 ? "" : "s" }}</span>

      <button
        type="button"
        class="btn btn-outline-danger btn-sm ms-auto"
        :disabled="!enabled"
        @click.prevent="emit('remove')"
      >
        Remove
      </button>
    </summary>

    <div class="card-body">
      <div class="row g-2 mb-2">
        <div class="col-md-4">
          <label
            class="form-label"
            :for="`${path}-category`"
          >Category <span class="text-danger">*</span></label>

          <select
            :id="`${path}-category`"
            class="form-select"
            :value="category"
            :disabled="!enabled"
            @change="setField('category', ($event.target as HTMLSelectElement).value)"
          >
            <option
              v-for="option in categories"
              :key="option"
              :value="option"
            >
              {{ label(option) }}
            </option>
          </select>
        </div>

        <div class="col-md-8">
          <label
            class="form-label"
            :for="`${path}-name`"
          >Name <span class="text-danger">*</span></label>

          <input
            :id="`${path}-name`"
            type="text"
            class="form-control"
            :value="name"
            :disabled="!enabled"
            @input="setField('name', ($event.target as HTMLInputElement).value)"
          >
        </div>
      </div>

      <div
        class="btn-group btn-group-sm mb-2"
        role="group"
        aria-label="This branch holds"
      >
        <button
          type="button"
          class="btn"
          :class="holdsProduct ? 'btn-primary' : 'btn-outline-primary'"
          :aria-pressed="holdsProduct"
          :disabled="!enabled"
          @click="!holdsProduct && setHolds(true)"
        >
          Product
        </button>

        <button
          type="button"
          class="btn"
          :class="holdsProduct ? 'btn-outline-primary' : 'btn-primary'"
          :aria-pressed="!holdsProduct"
          :disabled="!enabled"
          @click="holdsProduct && setHolds(false)"
        >
          Sub-branches
        </button>
      </div>

      <ul
        v-if="errors.length"
        class="text-danger small mb-2"
      >
        <li
          v-for="error in errors"
          :key="error"
        >
          {{ error }}
        </li>
      </ul>

      <dispatch-renderer
        v-if="holdsProduct"
        :schema="itemSchema"
        :uischema="{ type: 'Control', scope: '#/properties/product' }"
        :path="path"
        :enabled="enabled"
        :renderers="renderers"
        :cells="cells"
      />

      <template v-else>
        <BranchNode
          v-for="(child, index) in children"
          :key="`${path}.branches.${index}`"
          :branch="child"
          :path="`${path}.branches.${index}`"
          :item-schema="itemSchema"
          :depth="depth + 1"
          :enabled="enabled"
          :renderers="renderers"
          :cells="cells"
          :change="change"
          :new-branch="newBranch"
          :new-product="newProduct"
          :errors-at="errorsAt"
          @remove="setChildren(children.filter((_, i) => i !== index))"
        />

        <button
          type="button"
          class="btn btn-outline-primary btn-sm"
          :disabled="!enabled"
          @click="setChildren([...children, newBranch(category)])"
        >
          + Add {{ label(childCategory(category)) }}
        </button>
      </template>
    </div>
  </details>
</template>
