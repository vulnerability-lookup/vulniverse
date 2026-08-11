import {
  rankWith,
  schemaTypeIs,
} from "@jsonforms/core";

import type {
  JsonFormsRendererRegistryEntry,
  UISchemaElement,
} from "@jsonforms/core";

import AffectedRenderer from "./AffectedRenderer.vue";
import MetricsRenderer from "./MetricsRenderer.vue";
import ReferencesRenderer from "./ReferencesRenderer.vue";
import AdpRenderer from "./AdpRenderer.vue";
import ArrayCardRenderer from "./ArrayCardRenderer.vue";

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
