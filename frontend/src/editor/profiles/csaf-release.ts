import type {
  EditorDocument,
} from "../contracts";

/*
 * Releasing a CSAF 2.1 document: the tracking fields that change
 * together when a version is released (spec 3.1.19 "Version Type" and
 * the mandatory tests 6.1.14 to 6.1.22 and 6.1.66).
 *
 * - The first release turns a draft (0 or 0.y.z) into 1 or 1.0.0 and
 *   replaces the draft entries of the revision history, which a released
 *   document must not contain.
 * - Each later release raises the version and adds one revision entry.
 * - All dates of one release use the same instant.
 */

export type ReleaseKind = "initial" | "major" | "minor" | "patch";

export type ReleaseStatus = "final" | "interim";

export interface ReleaseInput {
  kind: ReleaseKind;
  status: ReleaseStatus;
  summary: string;
}

type JsonObject = Record<string, unknown>;

const INTEGER_VERSION = /^(0|[1-9][0-9]*)$/;
const SEMANTIC_VERSION = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;


function asObject(
  value: unknown,
): JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as JsonObject
    : {};
}


function tracking(
  document: EditorDocument,
): JsonObject {
  return asObject(asObject(asObject(document).document).tracking);
}


export function currentVersion(
  document: EditorDocument,
): string {
  const version = tracking(document).version;

  return typeof version === "string" ? version : "";
}


/** Integer versioning (1, 2, …) or semantic versioning (1.0.0, …). */
export function versioning(
  document: EditorDocument,
): "integer" | "semantic" {
  return INTEGER_VERSION.test(currentVersion(document)) ? "integer" : "semantic";
}


/** 0, 0.y.z or a pre-release: only allowed in draft documents. */
export function isDraftVersion(
  version: unknown,
): boolean {
  if (typeof version !== "string") {
    return false;
  }

  if (INTEGER_VERSION.test(version)) {
    return version === "0";
  }

  const match = SEMANTIC_VERSION.exec(version);

  return match !== null && (match[1] === "0" || /^[^+]*-/.test(version));
}


/** Released: status final or interim, with a released version number. */
export function isReleased(
  document: EditorDocument,
): boolean {
  const { status, version } = tracking(document);

  return (status === "final" || status === "interim") && !isDraftVersion(version);
}


export function nextVersion(
  version: string,
  kind: ReleaseKind,
): string {
  if (INTEGER_VERSION.test(version)) {
    return kind === "initial" ? "1" : String(Number(version) + 1);
  }

  if (kind === "initial") {
    return "1.0.0";
  }

  const match = SEMANTIC_VERSION.exec(version);
  const [major, minor, patch] = match
    ? [Number(match[1]), Number(match[2]), Number(match[3])]
    : [1, 0, 0];

  if (kind === "major") return `${major + 1}.0.0`;
  if (kind === "minor") return `${major}.${minor + 1}.0`;

  return `${major}.${minor}.${patch + 1}`;
}


/** The released document; `now` is an RFC 3339 instant. */
export function releaseCsaf(
  document: EditorDocument,
  input: ReleaseInput,
  now: string,
): EditorDocument {
  // Whole seconds, as the editor's date-time fields store them.
  const date = now.replace(/\.\d+Z$/, "Z");
  const root = asObject(document);
  const meta = asObject(root.document);
  const current = tracking(document);
  const version = nextVersion(currentVersion(document), input.kind);

  const history = Array.isArray(current.revision_history)
    ? current.revision_history
    : [];

  const kept = input.kind === "initial"
    ? history.filter((entry) => !isDraftVersion(asObject(entry).number))
    : history;

  return {
    ...root,
    document: {
      ...meta,
      tracking: {
        ...current,
        status: input.status,
        version,
        current_release_date: date,
        ...(input.kind === "initial" ? { initial_release_date: date } : {}),
        revision_history: [
          ...kept,
          { date, number: version, summary: input.summary },
        ],
      },
    },
  };
}
