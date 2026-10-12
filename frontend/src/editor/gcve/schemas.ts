export type JsonSchemaLike =
  Record<string, unknown>;


export function findGcveExtensionSchemas(
  schemaNode: unknown,
): Record<
  string,
  JsonSchemaLike
> {
  if (Array.isArray(schemaNode)) {
    for (const item of schemaNode) {
      const found =
        findGcveExtensionSchemas(
          item,
        );

      if (
        Object.keys(found).length >
        0
      ) {
        return found;
      }
    }

    return {};
  }

  if (
    schemaNode &&
    typeof schemaNode === "object"
  ) {
    const node =
      schemaNode as
        Record<string, unknown>;

    const properties =
      node.properties as
        | Record<string, unknown>
        | undefined;

    const xGcve =
      properties?.x_gcve as
        | Record<string, unknown>
        | undefined;

    const items =
      xGcve?.items as
        | Record<string, unknown>
        | undefined;

    const itemProperties =
      items?.properties as
        | Record<string, unknown>
        | undefined;

    const extensions =
      itemProperties?.extensions as
        | Record<string, unknown>
        | undefined;

    const extensionProperties =
      extensions?.properties as
        | Record<
            string,
            JsonSchemaLike
          >
        | undefined;

    if (extensionProperties) {
      return extensionProperties;
    }

    for (
      const value
      of Object.values(node)
    ) {
      const found =
        findGcveExtensionSchemas(
          value,
        );

      if (
        Object.keys(found).length >
        0
      ) {
        return found;
      }
    }
  }

  return {};
}
