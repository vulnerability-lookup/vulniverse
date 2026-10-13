import extensionSchemas from
  "@/generated/gcve/extension-schemas.json";


export type JsonSchemaLike =
  Record<string, unknown>;


/**
 * Registered GCVE extension schemas available to frontend
 * functionality such as the read-only extension preview.
 *
 * This data is generated directly from
 * schemas/extensions/gcve/registry.json and is intentionally
 * independent of any concrete GCVE editor profile.
 */
export const GCVE_EXTENSION_SCHEMAS =
  extensionSchemas as Record<
    string,
    JsonSchemaLike
  >;
