/*
 * Comparing a CSAF vulnerability with the public GCVE/CVE record it
 * cites. The public record arrives already converted to a CSAF
 * vulnerability (backend: csaf_from_cve), so both sides have one shape.
 */

type JsonObject = Record<string, unknown>;

const GCVE_ID = /^GCVE-\d+-\d{4}-\d+$/;

export interface Difference {
  field: string;
  label: string;
  ours: string;
  theirs: string;
  // Takes the public value into our vulnerability; absent when it can't
  // be taken over safely (scores refer to the record's own products).
  apply?: (vulnerability: JsonObject) => void;
}


function list(value: unknown): JsonObject[] {
  return Array.isArray(value)
    ? value.filter((item): item is JsonObject => typeof item === "object" && item !== null)
    : [];
}


function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}


function copy<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}


/** The CVE and GCVE IDs a vulnerability cites. */
export function vulnerabilityIds(vulnerability: JsonObject): string[] {
  const gcve = list(vulnerability.ids)
    .filter((id) => text(id.system_name).toUpperCase() === "GCVE" || GCVE_ID.test(text(id.text)))
    .map((id) => text(id.text));

  return [...new Set([text(vulnerability.cve), ...gcve].filter(Boolean))];
}


function description(vulnerability: JsonObject): string {
  return text(list(vulnerability.notes).find((note) => note.category === "description")?.text);
}


function cweIds(vulnerability: JsonObject): string {
  return list(vulnerability.cwes).map((cwe) => text(cwe.id)).sort().join(", ");
}


// "CVSS:3.1/AV:L/AC:L/…" with its metrics sorted: the same metrics in
// another order are the same vector.
function normalizeVector(vector: string): string {
  const [first = "", ...rest] = vector.split("/");

  return first.startsWith("CVSS:")
    ? [first, ...rest.sort()].join("/")
    : [first, ...rest].sort().join("/");
}


function vectors(vulnerability: JsonObject): string {
  return list(vulnerability.metrics)
    .flatMap((metric) => Object.values((metric.content ?? {}) as JsonObject))
    .map((score) => normalizeVector(text((score as JsonObject)?.vectorString)))
    .filter(Boolean)
    .sort()
    .join("\n");
}


function referenceUrls(vulnerability: JsonObject): string[] {
  return list(vulnerability.references).map((reference) => text(reference.url)).filter(Boolean);
}


/** What differs between our vulnerability and the public record's. */
export function differences(ours: JsonObject, theirs: JsonObject): Difference[] {
  const result: Difference[] = [];

  const add = (difference: Difference) => {
    if (difference.ours !== difference.theirs && difference.theirs) {
      result.push(difference);
    }
  };

  add({
    field: "title",
    label: "Title",
    ours: text(ours.title),
    theirs: text(theirs.title),
    apply: (target) => { target.title = theirs.title; },
  });

  add({
    field: "description",
    label: "Description",
    ours: description(ours),
    theirs: description(theirs),
    apply: (target) => {
      const notes = list(target.notes);
      const note = notes.find((entry) => entry.category === "description");

      if (note) {
        note.text = description(theirs);
      } else {
        target.notes = [...notes, { category: "description", title: "Vulnerability description", text: description(theirs) }];
      }
    },
  });

  add({
    field: "cve",
    label: "CVE ID",
    ours: text(ours.cve),
    theirs: text(theirs.cve),
    apply: (target) => { target.cve = theirs.cve; },
  });

  add({
    field: "cwes",
    label: "CWEs",
    ours: cweIds(ours),
    theirs: cweIds(theirs),
    apply: (target) => { target.cwes = copy(theirs.cwes); },
  });

  add({
    field: "disclosure_date",
    label: "Disclosure date",
    ours: text(ours.disclosure_date),
    theirs: text(theirs.disclosure_date),
    apply: (target) => { target.disclosure_date = theirs.disclosure_date; },
  });

  const ourUrls = referenceUrls(ours);
  const missing = list(theirs.references).filter((reference) => !ourUrls.includes(text(reference.url)));

  if (missing.length) {
    result.push({
      field: "references",
      label: "References",
      ours: `${ourUrls.length} references`,
      theirs: `${missing.length} more: ${missing.map((reference) => text(reference.url)).join(", ")}`,
      apply: (target) => { target.references = [...list(target.references), ...copy(missing)]; },
    });
  }

  add({ field: "cvss", label: "CVSS vectors", ours: vectors(ours), theirs: vectors(theirs) });

  return result;
}
