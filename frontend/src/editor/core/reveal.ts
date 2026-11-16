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
      return directField(element, path.split(".").slice(parts.length)) ?? element;
    }

    parts.pop();
  }

  return null;
}


/*
 * A card renderer that draws its fields itself (references, affected, …)
 * marks only the card, but a plain field of the card's own object is
 * still a JSON Forms control, whose id is "#/properties/<name>". Found,
 * it gets the full data-path, so the caller treats it as the field.
 */
function directField(card: HTMLElement, rest: string[]): HTMLElement | null {
  const [name] = rest;

  if (rest.length !== 1 || !name || /^\d+$/.test(name)) {
    return null;
  }

  const control = [...card.querySelectorAll<HTMLElement>(`[id="${CSS.escape(`#/properties/${name}`)}"]`)]
    // Not one of a nested card's fields.
    .find((element) => element.closest("[data-path]") === card);

  if (control) {
    control.dataset.path = [card.dataset.path, name].join(".");
  }

  return control ?? null;
}
