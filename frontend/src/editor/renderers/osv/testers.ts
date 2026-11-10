import type {
  JsonSchema,
} from "@jsonforms/core";


/**
 * The keys of an items schema made only of oneOf branches that each
 * allow exactly one required key ({"introduced": …} | {"fixed": …}),
 * or [] when the schema has any other shape.
 */
export function singleKeyChoices(
  schema: JsonSchema | undefined,
): string[] {
  const branches = schema?.oneOf;

  if (!Array.isArray(branches) || branches.length === 0) {
    return [];
  }

  const keys = branches.map((branch) => {
    const names = Object.keys(branch.properties ?? {});

    return names.length === 1
      && Array.isArray(branch.required)
      && branch.required.includes(names[0]!)
      ? names[0]!
      : null;
  });

  return keys.every((key) => key !== null) ? keys as string[] : [];
}
