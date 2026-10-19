<script setup lang="ts">
type AnyRecord = Record<string, unknown>;
type AnySchema = Record<string, unknown> | undefined;

const props = defineProps<{
  schema?: AnySchema;
  value: unknown;
}>();

function propertySchema(
  key: string,
): AnySchema {
  const properties = props.schema?.properties as
    | Record<string, AnySchema>
    | undefined;

  return properties?.[key];
}

function itemSchema(): AnySchema {
  return props.schema?.items as AnySchema;
}

function humanize(
  key: string,
): string {
  return key
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function titleFor(
  key: string,
): string {
  const title = propertySchema(key)?.title;

  return typeof title === "string" ? title : humanize(key);
}

function isPlainObject(
  candidate: unknown,
): candidate is AnyRecord {
  return typeof candidate === "object"
    && candidate !== null
    && !Array.isArray(candidate);
}

function isScalar(
  candidate: unknown,
): boolean {
  return candidate === null || typeof candidate !== "object";
}

function formatScalar(
  candidate: unknown,
): string {
  if (candidate === null || candidate === undefined || candidate === "") {
    return "—";
  }

  if (typeof candidate === "boolean") {
    return candidate ? "Yes" : "No";
  }

  return String(candidate);
}

// Driven by what's actually present in the value, not the schema's
// declared properties — an object may legitimately carry a key the
// schema doesn't know about (additionalProperties: true is the norm
// for these extensions), and it should still show up.
function objectEntries(
  value: AnyRecord,
): Array<[string, unknown]> {
  return Object.entries(value).filter(([, entryValue]) => entryValue !== undefined);
}
</script>

<template>
  <template v-if="Array.isArray(value)">
    <p
      v-if="value.length === 0"
      class="text-secondary small mb-0"
    >
      None.
    </p>

    <ul
      v-else-if="value.every(isScalar)"
      class="mb-0 small"
    >
      <li
        v-for="(item, index) in value"
        :key="index"
      >
        {{ formatScalar(item) }}
      </li>
    </ul>

    <div
      v-else
      class="d-flex flex-column gap-2"
    >
      <div
        v-for="(item, index) in value"
        :key="index"
        class="border rounded p-2"
      >
        <SchemaValuePreview
          :schema="itemSchema()"
          :value="item"
        />
      </div>
    </div>
  </template>

  <template v-else-if="isPlainObject(value)">
    <!--
      An object with exactly one property (e.g. a GCVE extension's
      own {ai_annotations: [...]} / {x_patch2vuln: {...}} wrapper) is
      unwrapped rather than given its own dt/dd row — that single
      property already carries the extension's *entire* content, so
      labeling it separately just adds a redundant heading and eats
      a third of the row's width (col-sm-4) for no real information;
      the card header above this component already names the
      extension. A genuinely multi-property object still gets full
      labeled rows below.
    -->
    <template v-if="objectEntries(value).length === 1">
      <template
        v-for="[key, entryValue] in objectEntries(value)"
        :key="key"
      >
        <SchemaValuePreview
          :schema="propertySchema(key)"
          :value="entryValue"
        />
      </template>
    </template>

    <dl
      v-else
      class="row mb-0 small"
    >
      <template
        v-for="[key, entryValue] in objectEntries(value)"
        :key="key"
      >
        <dt class="col-sm-4 text-secondary">{{ titleFor(key) }}</dt>

        <dd class="col-sm-8">
          <SchemaValuePreview
            :schema="propertySchema(key)"
            :value="entryValue"
          />
        </dd>
      </template>
    </dl>
  </template>

  <span v-else>{{ formatScalar(value) }}</span>
</template>
