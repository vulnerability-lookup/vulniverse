export function formatDate(
  value: unknown,
): string | null {
  if (
    typeof value !== "string"
    || value === ""
  ) {
    return null;
  }

  const date =
    new Date(value);

  return Number.isNaN(
    date.getTime(),
  )
    ? value
    : date.toLocaleString(
        undefined,
        {
          dateStyle: "medium",
          timeStyle: "short",
        },
      );
}


export function formatValue(
  value: unknown,
): string {
  return typeof value === "string"
    ? value
    : JSON.stringify(value);
}


export function isComplexValue(
  value: unknown,
): boolean {
  return (
    typeof value === "object"
    && value !== null
  );
}


export function formatValueJson(
  value: unknown,
): string {
  return JSON.stringify(
    value,
    null,
    2,
  );
}
