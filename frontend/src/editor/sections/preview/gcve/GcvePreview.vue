<script setup lang="ts">
import {
  GCVE_EXTENSION_SCHEMAS,
  extraGcveEntryEntries,
} from "../../../gcve";

import type {
  GcveOccurrence,
} from "../../../gcve";

import type {
  GcveExtension,
} from "../../../contracts";

import SchemaValuePreview from
  "../common/SchemaValuePreview.vue";

import {
  formatValue,
  formatValueJson,
  isComplexValue,
} from "../common/utils";


defineProps<{
  occurrences:
    GcveOccurrence[];
}>();


function extraGcveFields(
  extension: GcveExtension,
): Array<[string, unknown]> {
  return extraGcveEntryEntries(
    extension,
  );
}


function extensionsOf(
  extension: GcveExtension,
): Record<string, unknown> {
  const extensions =
    extension.extensions;

  return (
    extensions
    && typeof extensions
      === "object"
    && !Array.isArray(
      extensions,
    )
  )
    ? (
        extensions as
          Record<string, unknown>
      )
    : {};
}


/*
 * Registered extensions get a schema-driven recursive preview.
 * Unknown extension IDs remain visible as their raw JSON value.
 */
function registeredExtensionsOf(
  extension: GcveExtension,
): Array<[string, unknown]> {
  return Object.entries(
    extensionsOf(
      extension,
    ),
  ).filter(
    ([id]) =>
      id
      in GCVE_EXTENSION_SCHEMAS,
  );
}


function unrecognizedExtensionsOf(
  extension: GcveExtension,
): Array<[string, unknown]> {
  return Object.entries(
    extensionsOf(
      extension,
    ),
  ).filter(
    ([id]) =>
      !(
        id
        in GCVE_EXTENSION_SCHEMAS
      ),
  );
}


function extensionTitle(
  extensionId: string,
): string {
  const title =
    GCVE_EXTENSION_SCHEMAS[
      extensionId
    ]?.title;

  return typeof title
    === "string"
    ? title
    : extensionId;
}


function pathLabel(
  path: Array<
    string | number
  >,
): string {
  return path.length === 0
    ? "record root"
    : path.join(".");
}
</script>

<template>
  <div
    v-for="occurrence in occurrences"
    :key="
      pathLabel(
        occurrence.path
      )
    "
    class="card mb-4"
  >
    <div
      class="
        card-header
        d-flex
        align-items-center
        gap-2
      "
    >
      <span
        class="badge text-bg-secondary"
      >
        GCVE
      </span>

      <span class="fw-semibold">
        x_gcve
      </span>

      <span
        class="
          text-secondary
          small
        "
      >
        at
        {{
          pathLabel(
            occurrence.path
          )
        }}
      </span>
    </div>

    <div class="card-body">
      <div
        v-for="
          (
            extension,
            index
          ) in occurrence.extensions
        "
        :key="index"
        class="mb-3"
      >
        <div
          class="
            d-flex
            flex-wrap
            align-items-center
            gap-2
            mb-1
          "
        >
          <span class="fw-semibold">
            {{ extension.vulnId }}
          </span>

          <span
            v-if="
              extension.recordType
            "
            class="
              badge
              text-bg-light
              text-secondary
              border
            "
          >
            {{ extension.recordType }}
          </span>

          <span
            v-if="
              extension.language
            "
            class="
              badge
              text-bg-light
              text-secondary
              border
            "
          >
            {{ extension.language }}
          </span>
        </div>

        <ul
          v-if="
            extension.relationships
              ?.length
          "
          class="small mb-2"
        >
          <li
            v-for="
              (
                relationship,
                relIndex
              ) in extension.relationships
            "
            :key="relIndex"
          >
            <span
              v-if="
                relationship.srcId
              "
            >
              {{ relationship.srcId }}
            </span>
            {{ relationship.type }}
            {{ relationship.destId }}
          </li>
        </ul>

        <dl
          v-if="
            extraGcveFields(
              extension
            ).length
          "
          class="row mb-0 small"
        >
          <template
            v-for="
              [
                key,
                value,
              ] in extraGcveFields(
                extension
              )
            "
            :key="key"
          >
            <dt
              class="
                col-sm-3
                text-secondary
              "
            >
              {{ key }}
            </dt>

            <dd
              v-if="
                isComplexValue(
                  value
                )
              "
              class="col-sm-9"
            >
              <details>
                <summary
                  class="text-secondary"
                >
                  Show details
                </summary>

                <pre
                  class="
                    preview-json-value
                    mb-0
                    mt-1
                  "
                >{{ formatValueJson(value) }}</pre>
              </details>
            </dd>

            <dd
              v-else
              class="col-sm-9"
            >
              {{ formatValue(value) }}
            </dd>
          </template>
        </dl>

        <div
          v-for="
            [
              extensionId,
              extensionValue,
            ] in registeredExtensionsOf(
              extension
            )
          "
          :key="extensionId"
          class="card mt-2"
        >
          <div
            class="
              card-header
              small
              fw-semibold
            "
          >
            {{
              extensionTitle(
                extensionId
              )
            }}
          </div>

          <div class="card-body">
            <SchemaValuePreview
              :schema="
                GCVE_EXTENSION_SCHEMAS[
                  extensionId
                ]
              "
              :value="
                extensionValue
              "
            />
          </div>
        </div>

        <dl
          v-if="
            unrecognizedExtensionsOf(
              extension
            ).length
          "
          class="
            row
            mb-0
            small
            mt-2
          "
        >
          <template
            v-for="
              [
                extensionId,
                extensionValue,
              ] in unrecognizedExtensionsOf(
                extension
              )
            "
            :key="extensionId"
          >
            <dt
              class="
                col-sm-3
                text-secondary
              "
            >
              extensions.{{
                extensionId
              }}
            </dt>

            <dd class="col-sm-9">
              <details>
                <summary
                  class="text-secondary"
                >
                  Show details
                </summary>

                <pre
                  class="
                    preview-json-value
                    mb-0
                    mt-1
                  "
                >{{ formatValueJson(extensionValue) }}</pre>
              </details>
            </dd>
          </template>
        </dl>
      </div>
    </div>
  </div>
</template>


<style scoped>
.preview-json-value {
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 20rem;
  overflow-y: auto;
}
</style>
