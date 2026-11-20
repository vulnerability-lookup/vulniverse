/**
 * The options to suggest for what's typed: those containing it (any
 * case), or all of them when it's empty or already one of the options,
 * so a filled-in field still shows the alternatives.
 */
export function matchingOptions(options: readonly string[], query: string): string[] {
  const needle = query.trim().toLowerCase();

  if (!needle || options.some((option) => option.toLowerCase() === needle)) {
    return [...options];
  }

  return options.filter((option) => option.toLowerCase().includes(needle));
}
