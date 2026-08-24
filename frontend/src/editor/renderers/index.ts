import {
  and,
  isBooleanControl,
  isStringControl,
  rankWith,
  schemaMatches,
  schemaTypeIs,
} from "@jsonforms/core";

import type {
  ControlElement,
  JsonFormsRendererRegistryEntry,
  UISchemaElement,
} from "@jsonforms/core";

import { MultiStringControlRenderer } from "@jsonforms/vue-vanilla";

import AffectedRenderer from "./AffectedRenderer.vue";
import MetricsRenderer from "./MetricsRenderer.vue";
import ReferencesRenderer from "./ReferencesRenderer.vue";
import AdpRenderer from "./AdpRenderer.vue";
import GcveExtensionRenderer from "./GcveExtensionRenderer.vue";
import SourceRenderer from "./SourceRenderer.vue";
import TagsRenderer from "./TagsRenderer.vue";
import ArrayCardRenderer from "./ArrayCardRenderer.vue";
import BooleanSelectRenderer from "./BooleanSelectRenderer.vue";

/*
 * Any string property whose schema allows at least this many
 * characters is free-form prose rather than a short label —
 * descriptions/timeline/credits/configurations/workarounds/
 * solutions/exploits/rejectedReasons all share the CVE schema's own
 * "value" free-text shape, maxLength 4096 (supportingMedia's value
 * is 16384). Detected straight from the schema, not a per-field
 * list, so it keeps working if the schema grows more fields shaped
 * like this. `title` (256), `vendor` (512), and `product`/
 * `packageName` (2048) stay single-line.
 */
const LONG_TEXT_MIN_LENGTH = 4096;

/*
 * Excludes a bare array-item control (scope "#", e.g. an entry in
 * Modules/CPEs/Platforms) — ArrayCardRenderer dispatches those with
 * the array's own maxLength, which for a few primitive-item arrays
 * happens to be 4096 too despite holding short enumerable values,
 * not prose.
 */
const isLongTextControl = and(
  isStringControl,
  (uischema: UISchemaElement) => (uischema as ControlElement).scope !== "#",
  schemaMatches(
    (schema) => typeof schema.maxLength === "number" && schema.maxLength >= LONG_TEXT_MIN_LENGTH,
  ),
);

/*
 * schemas/editor/cve.layout.json tags containers.cna.affected /
 * metrics / references with options.renderer = "vulniverse-*".
 * Rank 10 beats both the vanilla array renderer (rank 2) and
 * ArrayCardRenderer (rank 5) below, so these win whenever that
 * option is present.
 */
function rendererOptionIs(
  name: string,
) {
  return rankWith(
    10,
    (uischema: UISchemaElement) => {
      const options = (
        uischema as { options?: { renderer?: string } }
      ).options;

      return options?.renderer === name;
    },
  );
}

export const customRenderers: JsonFormsRendererRegistryEntry[] = [
  {
    renderer: AffectedRenderer,
    tester: rendererOptionIs("vulniverse-affected"),
  },
  {
    renderer: MetricsRenderer,
    tester: rendererOptionIs("vulniverse-metrics"),
  },
  {
    renderer: ReferencesRenderer,
    tester: rendererOptionIs("vulniverse-references"),
  },
  {
    renderer: AdpRenderer,
    tester: rendererOptionIs("vulniverse-adp"),
  },
  {
    renderer: GcveExtensionRenderer,
    tester: rendererOptionIs("vulniverse-gcve-extension"),
  },
  {
    renderer: SourceRenderer,
    tester: rendererOptionIs("vulniverse-source"),
  },
  {
    renderer: TagsRenderer,
    tester: rendererOptionIs("vulniverse-tags"),
  },
  /*
   * Rank 2 beats vanilla's own checkbox-based BooleanControlRenderer
   * (rank 1) for every boolean field — see BooleanSelectRenderer.vue
   * for why.
   */
  {
    renderer: BooleanSelectRenderer,
    tester: rankWith(2, isBooleanControl),
  },
  /*
   * Reuses vanilla's own textarea control (normally opt-in via
   * uischema `options.multi`) but with a schema-driven tester
   * instead, so no per-field uischema configuration is needed. Rank
   * 3 beats vanilla's plain single-line StringControlRenderer
   * (rank 1) and its own opt-in multi tester (rank 2) wherever the
   * schema itself signals long-form text.
   */
  {
    renderer: MultiStringControlRenderer,
    tester: rankWith(3, isLongTextControl),
  },
  /*
   * Default styling for every other array field — object items
   * (Descriptions, Credits, Timeline, supportingMedia, versions,
   * changes, ...) and primitive items alike (Cpes, Modules,
   * Program Files, Platforms, ...) — same card look and add/
   * remove buttons as the three named renderers above, minus
   * their field-specific curation. schemaTypeIs('array') is
   * exactly what vanilla's own ArrayListRenderer tests for, so
   * this covers its entire scope; rank 5 beats it (rank 2) but
   * loses to the three named renderers (rank 10) wherever those
   * apply instead.
   */
  {
    renderer: ArrayCardRenderer,
    tester: rankWith(5, schemaTypeIs("array")),
  },
];
