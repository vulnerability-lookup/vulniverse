/*
 * Showing a field in the Editor section by its data path (dot notation,
 * as JSON Forms uses: "containers.cna.affected.2.vendor"). The tab
 * renderer, the collapsible cards and the form section each react to the
 * editor state's `reveal` request; these helpers are what they share.
 */

/** `path` is `prefix` itself or lies below it. */
export function isWithin(
  path: string,
  prefix: string,
): boolean {
  return prefix === "" || path === prefix || path.startsWith(`${prefix}.`);
}


/** The array item of `arrayPath` that `path` lies in, or null. */
export function itemIndex(
  path: string,
  arrayPath: string,
): number | null {
  if (!path.startsWith(`${arrayPath}.`)) {
    return null;
  }

  const segment = path.slice(arrayPath.length + 1).split(".")[0] ?? "";

  return /^\d+$/.test(segment) ? Number(segment) : null;
}


/**
 * The element marked with `path` (data-path), or the closest marked
 * parent when the field itself isn't drawn as its own element.
 */
export function revealTarget(
  root: ParentNode,
  path: string,
): HTMLElement | null {
  const parts = path.split(".");

  while (parts.length) {
    const selector = `[data-path="${CSS.escape(parts.join("."))}"]`;
    const element = root.querySelector<HTMLElement>(selector);

    if (element) {
      return element;
    }

    parts.pop();
  }

  return null;
}
