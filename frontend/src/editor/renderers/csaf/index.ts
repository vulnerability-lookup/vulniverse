import {
  and,
  rankWith,
  schemaMatches,
  uiTypeIs,
} from "@jsonforms/core";

import type {
  ControlElement,
  JsonFormsRendererRegistryEntry,
  Tester,
} from "@jsonforms/core";

import BranchesRenderer from
  "./BranchesRenderer.vue";

import CvssRenderer from
  "./CvssRenderer.vue";

import ReferenceRenderer from
  "./ReferenceRenderer.vue";

import {
  cvssVersions,
} from "./cvss";

import {
  definitionOf,
  referenceKind,
} from "./products";


// Where a product or group ID is defined rather than referred to
// (full_product_name.product_id, product_groups[].group_id): plain text.
const DEFINING_PROPERTIES = ["/product_id", "/group_id"];

export const isReferenceControl: Tester = (uischema, schema, context) => {
  if (uischema.type !== "Control") {
    return false;
  }

  const scope = (uischema as ControlElement).scope;

  return schemaMatches((controlSchema) => {
    const kind = referenceKind(controlSchema);

    return kind !== undefined
      && (kind.list || !DEFINING_PROPERTIES.some((property) => scope.endsWith(property)));
  })(uischema, schema, context);
};


// All above ArrayCardRenderer and the composite-object JSON box (5).
export const CSAF_RENDERERS:
  JsonFormsRendererRegistryEntry[] = [
    {
      renderer:
        CvssRenderer,

      // FIRST CVSS objects (metrics content.cvss_v2/v3/v4).
      tester:
        rankWith(
          7,
          and(
            uiTypeIs("Control"),
            schemaMatches((schema) => cvssVersions(schema).length > 0),
          ),
        ),
    },

    {
      renderer:
        BranchesRenderer,

      tester:
        rankWith(
          7,
          and(
            uiTypeIs("Control"),
            schemaMatches((schema) => definitionOf(schema) === "branches_t"),
          ),
        ),
    },

    {
      renderer:
        ReferenceRenderer,

      tester:
        rankWith(7, isReferenceControl),
    },
  ];
