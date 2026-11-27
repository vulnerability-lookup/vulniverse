---
icon: lucide/database
---

# The repository

The editor stores nothing itself. Everything it loads, saves, validates or
publishes goes through the **repository**: one JavaScript object your
application assigns to the element.

```js
editor.repository = myRepository;
```

Four methods are required, for loading and saving. Everything else is
optional and grouped by feature: implement a group and the matching panel
or field works; leave it out and the editor shows a "not supported here"
message or falls back to plain input, nothing breaks.

All methods return promises. The exact TypeScript signatures are in
`vulniverse-editor.d.ts`, shipped with the npm package and next to every
release's bundle (`EditorRepository` and the types below).

## Errors

- **Anything goes wrong:** throw an `Error` with a message for the user.
  The editor shows the message and sends it as an
  [`error` event](element.md#events).
- **A save is refused because the record is invalid:** throw the
  `RecordValidationError` the bundle exports, with the errors in the
  `ValidationResult` format below. The editor then marks the fields in
  the form, as Validate does, and sends no `error` event.

```js
import { RecordValidationError } from "@nmd03/vulniverse";

throw new RecordValidationError("The record is invalid.", result.errors);
```

- **The publishing panels need more detail** (see
  [Publishing](#publishing-to-vulnerability-lookup-or-the-cve-program)):
  throw the exported `EditorRepositoryError`, with an HTTP-style status
  and details, `new EditorRepositoryError(message, status, details)`.

## Loading and saving (required)

| Method | Returns | Called |
| --- | --- | --- |
| `loadRecord(identifier)` | `LoadedRecord` | When the element starts in `mode="edit"`, on Reload, and when `record-id` changes. |
| `createRecord(record, profile, isDraft)` | `LoadedRecord` | On the first save of a new record. |
| `updateRecord(identifier, record, profile, isDraft)` | `LoadedRecord` | On every later save. |
| `validateRecord(record, profile)` | `ValidationResult` | When the user clicks Validate. |

`record` is the record's JSON, `profile` its profile (`"gcve-bcp-05-1.7"`,
`"cve-5.2.0"` or `"osv-1.9.2"`), and `isDraft` whether it's saved as a
draft (see [Draft and publish buttons](#draft-and-publish-buttons)).

```ts
interface LoadedRecord {
  identifier: string;               // your key for the record
  vulnerabilityId?: string | null;  // its CVE/GCVE/OSV ID, shown as the title
  profile: string;
  record: object;                   // the record's JSON
  isDraft: boolean;
}
```

- `identifier` is whatever stable key you address the record by: a
  database ID, a UUID, or the vulnerability ID itself. The editor only
  hands it back to you.
- `vulnerabilityId` is shown as the record's name; `null` means "no ID
  yet", and leaving it out shows `identifier` instead. For GCVE records the
  ID is the `vulnId` of the `x_gcve` entry whose `recordType` is
  `"advisory"`.
- Return the record **as stored**, not the object you were given: the
  editor treats the returned record as the new "last saved" state, which
  its change tracking compares against.

```ts
interface ValidationResult {
  valid: boolean;
  profile: string;
  errors: Array<{
    path: Array<string | number>;        // where, e.g. ["containers", "cna", "title"]
    schemaPath: Array<string | number>;
    message: string;
    validator?: string;                  // e.g. "required"
    severity?: "error" | "warning";
  }>;
}
```

How to validate on your server, with the official schemas: [Embed it,
step 6](../quickstart/embed.md#6-validate-on-your-server).

## Deleting

| Method | Returns |
| --- | --- |
| `deleteRecord(identifier)` | nothing |

Without it, the editor has no Delete button. After a delete it sends a
[`deleted` event](element.md#events); your application decides where to
go next.

## Draft and publish buttons

`lifecycleTransitions` is a property, not a method. It decides which
draft/publish buttons the header shows; each one saves with `isDraft` set
to its `targetIsDraft`.

| Value | Buttons |
| --- | --- |
| Not set | **Publish** while a draft, **Revert to draft** once published (the standalone app's behaviour). |
| `[]` | None: your application has no drafts. |
| Your own list | `{ id, label, targetIsDraft, isVisible?(context) }` each. |

## CWE and CAPEC lists

| Method | Returns |
| --- | --- |
| `getReferenceList(kind)` | `Array<{ id: string; name: string }>` |

`kind` is `"cwe"` or `"capec"`, and the list is everything the user can
pick from, e.g. `{ id: "CWE-79", name: "Improper Neutralization of Input
During Web Page Generation" }`. Without it, CWE and CAPEC fields are plain
text fields.

## CPE suggestions

Called while the user types, for suggestions in the vendor, product and
CPE name fields. Each one is optional on its own.

| Method | Returns |
| --- | --- |
| `searchCpeVendors(q)` | `Array<{ id: string; name: string; title?: string \| null }>` |
| `searchCpeProducts(q, vendorQ?)` | the same shape; `vendorQ` narrows to the vendor field's text |
| `searchCpes(params)` | `Array<{ id: string; cpe: string; title?: string \| null; part: "a" \| "o" \| "h"; version: string; deprecated: boolean }>` |

`params` is `{ q?, vendorQ?, productQ?, part? }`. Return a short list
(the first matches), not everything.

## Templates

For the [Templates panel](element.md#panels-and-actions). Implement all
four.

| Method | Returns |
| --- | --- |
| `listTemplates(profile)` | `Template[]` |
| `saveTemplate(profile, name, fields)` | the new `Template` |
| `updateTemplate(id, name, fields)` | the updated `Template` |
| `deleteTemplate(id)` | nothing |

```ts
interface Template {
  id: string;
  profile: string;   // a template only applies to records of its profile
  name: string;
  fields: Array<{
    path: string;    // a dot path in the record, e.g. "containers.cna.affected.0.vendor"
    value: unknown;
  }>;
}
```

`listTemplates` returns only the given profile's templates.

## Publishing to Vulnerability-Lookup or the CVE Program

For the `vulnerabilityLookupPanel` and `cveProgramPanel`. `target` is
`"vl"` or `"cve-program"`, and `recordIdentifier` your `identifier`.
Implement the first five together; the last three are optional on their
own.

| Method | Returns |
| --- | --- |
| `getCnaPublication(target, recordIdentifier)` | `CnaPublication` |
| `reserveCveId(target, recordIdentifier, year)` | `CnaPublication` |
| `publishCna(target, recordIdentifier)` | `CnaPublication` |
| `rejectCna(target, recordIdentifier, reason)` | `CnaPublication` |
| `abortCna(target, recordIdentifier)` | `CnaPublication` |
| `getUpstreamCna(target, recordIdentifier)` | the record as published upstream, for the comparison |
| `unlinkCna(target, recordIdentifier)` | `CnaPublication`: the link removed, the ID kept upstream |
| `pullCna(target, recordIdentifier, cveId)` | `{ publication: CnaPublication; record: object \| null }`: links an existing ID; `record` is upstream's, `null` while only reserved |

```ts
interface CnaPublication {
  id: number;
  recordId: number;
  target: "vl" | "cve-program";
  status: string;            // see below
  cveId: string | null;      // the reserved CVE or GCVE ID
  reservedAt: string | null; // ISO 8601 dates
  publishedAt: string | null;
  rejectedAt: string | null;
  lastSentAt?: string | null;
  lastError: string | null;  // shown to the user
  createdAt: string;
  updatedAt: string;
}
```

`status` is one of `LOCAL_ONLY`, `RESERVATION_PENDING`, `RESERVED`,
`PUBLICATION_PENDING`, `PUBLISHED`, `REJECTION_PENDING`, `REJECTED` or
`ABORTED`. For a record that was never reserved, return a publication with
`LOCAL_ONLY` rather than an error.

`publishCna` publishes the record **as saved**: the panel saves pending
edits first. If upstream refuses the record as invalid, throw
`RecordValidationError` so the fields are marked.

The panels understand three more cases, thrown as `EditorRepositoryError`:

| Throw | The panel shows |
| --- | --- |
| `new EditorRepositoryError(message, 409)` | "*Vulnerability-Lookup* isn't configured on this deployment", e.g. no CNA credentials for this user |
| `new EditorRepositoryError(message, 409, { code: "CHANGED_MEANWHILE" })` | `message`: someone else saved the record meanwhile |
| `new EditorRepositoryError(message, status, { publication })` | the updated `publication` and its `lastError`, e.g. the upstream server's reply, instead of `message` |

## Record quality

The `recordQualityPanel` needs no method: since 1.1 it scores the record
in the browser. `scoreRecordQuality(record, profile)`, which it used
before, is deprecated and no longer called; it stays in the type
definitions until 2.0, so existing repositories keep type-checking.

The panel's score has this shape (exported as `RecordQualityScore`):

```ts
interface RecordQualityScore {
  score: number;              // e.g. 85
  grade: string;              // e.g. "B"
  methodologyVersion: number;
  pillars: Array<{ id: string; label: string; points: number; maximum: number }>;
  checks: Array<{
    id: string;
    label: string;
    pillar: string;           // the id of its pillar
    credit: number;           // 0 to 1
    weight: number;
    points: number;
    rule: string;             // what the check looks for
  }>;
}
```

## Patch2Vuln

For the `patch2vulnPanel`: an analysis of a patch that runs as a
background job. `submitPatch2VulnJob` and `getPatch2VulnJob` are needed
together; the other two are optional.

| Method | Returns |
| --- | --- |
| `submitPatch2VulnJob(input)` | `Patch2VulnJob` |
| `getPatch2VulnJob(jobId)` | `Patch2VulnJob` |
| `cancelPatch2VulnJob(jobId)` | `Patch2VulnJob`; a queued job ends at once, a running one once its worker stops |
| `subscribeJobEvents(jobId, onStatus, onDisconnect?)` | a function that stops the subscription |

```ts
interface Patch2VulnInput {
  commitUrls: string[];
  files: File[];               // uploaded patch files
  context: {                   // all optional, given to the analysis
    vendor?: string;
    product?: string;
    affectedVersion?: string;
    fixedVersion?: string;
    versionType?: string;
    packageUrl?: string;
    osvEcosystem?: string;
    prompt?: string;           // the user's additional instructions
  };
}

interface Patch2VulnJob {
  jobId: string;
  status: "queued" | "running" | "completed" | "failed" | "canceled";
  workerAvailable?: boolean;
  result?: {                   // once completed
    record: object;            // the generated CVE record
    osv?: object | null;       // and OSV record, for OSV profiles
    analysis: unknown;
  };
  error?: string;              // once failed
}
```

Without `subscribeJobEvents`, the panel checks the job with
`getPatch2VulnJob` every 2 seconds while it's open, and every 10 seconds
in the background. With it, the panel gets live updates instead: call
`onStatus({ jobId, status, error? })` on every change and `onDisconnect()`
if the connection drops, and return a function that stops it.

## ML suggestions

For the `mlGatewayPanel`: severity and MITRE ATT&CK suggestions for the
record's English description, from an
[ML-Gateway](https://github.com/vulnerability-lookup/ML-Gateway). Both
methods are needed. Call the gateway from your server, not from the
browser: its endpoints have no authentication. Vulnerability-Lookup's
`/api/vlai/severity-classification` and `/api/vlai/attack-techniques`
already do that.

| Method | Returns |
| --- | --- |
| `classifySeverity(description)` | `SeverityPrediction` |
| `classifyAttackTechniques(description, topK)` | `{ techniques: AttackTechniquePrediction[]; model? }` |

```ts
interface SeverityPrediction {
  severity: string;            // the model's label, e.g. "High"
  confidence: number;          // 0 to 1
  model?: string | null;
}

interface AttackTechniquePrediction {
  id: string;                  // e.g. "T1190"
  name: string;
  score: number;               // 0 to 1, per technique
  predicted: boolean;          // the model's own pick (score >= 0.5)
}
```

The panel adds the techniques the user ticks to
`containers.cna.taxonomyMappings`, under `taxonomyName: "ATT&CK"`, each
with `relationshipName: "maps to"` and the technique's name as
`relationshipValue` (its ID when the name is empty). The severity is
only shown.

## Examples to start from

- **A minimal repository** that keeps one record in the browser: the
  complete page in [Embed it, step 5](../quickstart/embed.md#5-a-complete-page).
- **The standalone app's** `HttpRepository`
  ([`frontend/src/repositories/HttpRepository.ts`](https://github.com/vulnerability-lookup/vulniverse/blob/main/frontend/src/repositories/HttpRepository.ts)):
  every method, against the Vulniverse backend's `/api/v1`. Its one
  option is that base URL: `new HttpRepository("/api/v1")`.
- **Vulnerability-Lookup's** `VulnerabilityLookupRepository`: the
  loading, saving, reference lists, templates, quality and Patch2Vuln
  methods against another application's own API; see
  [Embedding: Vulnerability-Lookup](vl.md).
