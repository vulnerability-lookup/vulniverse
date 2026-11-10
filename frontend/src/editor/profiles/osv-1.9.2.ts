import {
  markRaw,
} from "vue";

import type {
  JsonSchema,
  UISchemaElement,
} from "@jsonforms/core";

import authoringSchema from
  "@/generated/schemas/osv-1.9.2/authoring.schema.json";

import uiSchema from
  "@/generated/schemas/osv-1.9.2/ui.schema.json";

import fieldPaths from
  "@/generated/schemas/osv-1.9.2/field-paths.json";

import {
  OsvPreviewSection,
} from "../sections/preview/osv";

import {
  COMMON_RENDERERS,
  GCVE_RENDERERS,
  OSV_RENDERERS,
} from "../renderers";

import type {
  EditorProfileDefinition,
} from "./types";


export const osv192Profile:
  EditorProfileDefinition = {
  id: "osv-1.9.2",

  label: "OSV",

  description:
    "An Open Source Vulnerability (OSV) 1.9.2 record.",

  schema:
    // The inferred JSON type is too narrow to cast directly.
    authoringSchema as unknown as JsonSchema,

  uiSchema:
    uiSchema as UISchemaElement,

  fieldPaths,

  createEmptyDocument() {
    return {
      schema_version: "1.9.2",
      id: "",
      modified: new Date().toISOString(),
      affected: [],
    };
  },

  renderers: [
    ...COMMON_RENDERERS,
    ...OSV_RENDERERS,
    // database_specific.x_gcve (GCVE-BCP-05 data from patch2vuln).
    ...GCVE_RENDERERS,
  ],

  previewComponent:
    markRaw(OsvPreviewSection),
};
