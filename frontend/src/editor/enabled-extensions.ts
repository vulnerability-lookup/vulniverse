/**
 * Filters a BUILTIN_PANELS/BUILTIN_MODULES list down to the ids
 * enabled by config/vulniverse.toml (fetched via
 * HttpRepository.getCapabilities()). An id absent from the flags —
 * no config file, or the id just isn't mentioned — defaults to
 * enabled, so a deployment with no config behaves exactly like one
 * with everything turned on.
 */
export function filterEnabled<T extends { id: string }>(
  items: T[],
  flags: Record<string, boolean>,
): T[] {
  return items.filter((item) => flags[item.id] ?? true);
}
