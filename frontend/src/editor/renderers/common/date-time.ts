/*
 * Conversions between a stored UTC timestamp ("2026-12-28T23:59:59Z",
 * optionally with fractions) and a <input type="datetime-local">
 * value ("2026-12-28T23:59:59"). The stock JSON Forms control cut the
 * value to minutes and wrote back ":00.000Z", losing seconds.
 */

const PICKER_PREFIX = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?/;


/** The picker value for a stored timestamp, or "" when it isn't one. */
export function toPickerValue(
  stored: unknown,
): string {
  if (typeof stored !== "string") {
    return "";
  }

  const match = PICKER_PREFIX.exec(stored);

  if (!match) {
    return "";
  }

  return match[1] ? match[0] : `${match[0]}:00`;
}


/**
 * The UTC timestamp to store for a picker value, or undefined when the
 * picker was cleared. Browsers leave out ":SS" when the seconds are 0.
 */
export function fromPickerValue(
  picker: string,
): string | undefined {
  const match = PICKER_PREFIX.exec(picker);

  if (!match) {
    return undefined;
  }

  return `${match[1] ? match[0] : `${match[0]}:00`}Z`;
}
