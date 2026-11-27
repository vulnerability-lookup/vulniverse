import type {
  JsonSchema,
  UISchemaElement,
} from "@jsonforms/core";

import authoringSchema from
  "@/generated/schemas/euvd-1.0/authoring.schema.json";

import uiSchema from
  "@/generated/schemas/euvd-1.0/ui.schema.json";

import fieldPaths from
  "@/generated/schemas/euvd-1.0/field-paths.json";

import {
  COMMON_RENDERERS,
} from "../renderers";

import type {
  EditorProfileDefinition,
} from "./types";


// A record of the European Vulnerability Database that ENISA writes itself,
// for a vulnerability with no CVE. Its identifier is reserved by the EUVD
// when the record is first saved, so a new record has none.
export const euvd10Profile:
  EditorProfileDefinition = {
  id: "euvd-1.0",

  label: "EUVD",

  description:
    "A European Vulnerability Database (EUVD) record, for a vulnerability with no CVE.",

  schema:
    // The inferred JSON type is too narrow to cast directly.
    authoringSchema as unknown as JsonSchema,

  uiSchema:
    uiSchema as UISchemaElement,

  fieldPaths,

  createEmptyDocument() {
    return {
      title: "",
      description: "",
      references: [],
      affected: [],
    };
  },

  renderers: [
    ...COMMON_RENDERERS,
  ],

  // Only Vulnerability-Lookup, which reserves the EUVD ID, creates these
  // records; the standalone app could never give one an identifier.
  standalone: false,
};
