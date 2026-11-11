import {
  createAjv,
} from "@jsonforms/core";

import type {
  JsonSchema,
} from "@jsonforms/core";

import Ajv2020 from "ajv/dist/2020";

import addFormats from "ajv-formats";

import type Ajv from "ajv";

import type {
  AnySchema,
  ValidateFunction,
} from "ajv";


function addEditorFormats(
  ajv: Ajv,
): Ajv {
  ajv.addFormat(
    "long-text",
    {
      type: "string",
      validate: () => true,
    },
  );

  return ajv;
}


// Draft-07: CVE, GCVE and OSV authoring schemas.
export const editorAjv =
  addEditorFormats(createAjv());


// JSON Schema 2020-12 (CSAF), so unevaluatedItems and dependentRequired
// are checked in the editor too. Same options as JSON Forms' createAjv.
export const editorAjv2020 = (() => {
  const ajv = new Ajv2020({
    allErrors: true,
    verbose: true,
    strict: false,
    addUsedSchema: false,
  });

  addFormats(ajv);

  // JSON Forms shows a missing-property error on the missing field only
  // for "required" and draft-07's "dependencies"; it would drop
  // dependentRequired (same params) on the parent object, where no control
  // shows it. So its errors are renamed after validation.
  const compile = ajv.compile.bind(ajv);

  ajv.compile = ((schema: AnySchema) => {
    const validate = compile(schema);

    const renamed = ((data: unknown) => {
      const valid = validate(data);

      renamed.errors = validate.errors?.map((error) => (
        error.keyword === "dependentRequired"
          ? { ...error, keyword: "dependencies" }
          : error
      )) ?? null;

      return valid;
    }) as ValidateFunction;

    return renamed;
  }) as typeof ajv.compile;

  return addEditorFormats(ajv);
})();


const DRAFT_2020_12 =
  "https://json-schema.org/draft/2020-12/schema";


/**
 * The validator for a generated authoring schema: one Ajv instance
 * compiles a single dialect, and the generator states it in $schema.
 */
export function ajvForSchema(
  schema: JsonSchema,
): Ajv {
  return (schema as { $schema?: string }).$schema === DRAFT_2020_12
    ? editorAjv2020
    : editorAjv;
}
