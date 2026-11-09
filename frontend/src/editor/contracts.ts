import type {
  Component,
} from "vue";

export type EditorDocument =
  Record<string, unknown>;

export interface Description {
  lang: string;
  value: string;
  supportingMedia?: unknown[];
}

export interface GcveRelationship {
  destId: string;
  type: string;
  srcId?: string;
}

export interface GcveExtension {
  /*
   * Absent until a real GCVE ID is assigned (e.g. an entry freshly
   * merged from a generator like Patch2Vuln, before reservation) —
   * the schema requires it on a published record, but the editor
   * allows an incomplete draft to exist without one.
   */
  vulnId?: string;
  recordType: string;
  relationships?: GcveRelationship[];
  language?: string;

  [key: string]: unknown;
}

export interface CveMetadata {
  cveId?: string;
  vulnId?: string;
  state?: string;

  /*
   * Preserve properties the editor does not yet understand.
   */
  [key: string]: unknown;
}

export interface ProviderMetadata {
  orgId?: string;
  shortName?: string;
  dateUpdated?: string;

  [key: string]: unknown;
}

export interface CnaContainer {
  descriptions?: Description[];
  affected?: unknown[];
  references?: unknown[];

  x_gcve?: GcveExtension[];

  /*
   * A rejected CNA container is a different, minimal shape from the
   * one above (schemas/upstream/cve/5.2.0's cnaRejectedContainer:
   * additionalProperties false, only these three) — descriptions/
   * affected/references above don't apply to it at all.
   */
  providerMetadata?: ProviderMetadata;
  rejectedReasons?: Description[];
  replacedBy?: string[];

  [key: string]: unknown;
}

export interface RecordContainers {
  cna?: CnaContainer;
  adp?: unknown[];

  [key: string]: unknown;
}

export interface CveRecord {
  dataType?: string;
  dataVersion?: string;
  cveMetadata?: CveMetadata;
  containers?: RecordContainers;
  // x_gcve?: GcveExtension[];

  /*
   * Records may contain extensions that Vulniverse does not
   * currently render. Those must remain in the object.
   */
  [key: string]: unknown;
}

export interface LoadedRecord {
  /** Opaque key the repository addresses this record by (the standalone
   * app uses its database id; a host may use anything stable). */
  identifier: string;
  /** The CVE/GCVE/OSV identifier, for display only. null = the record
   * has none yet. Omitted by a host whose key already is that
   * identifier — the editor then shows `identifier` instead. */
  vulnerabilityId?: string | null;
  profile: string;
  record: EditorDocument;
  isDraft: boolean;
}

export interface ValidationError {
  path: Array<string | number>;
  schemaPath: Array<string | number>;
  message: string;
  validator?: string;
  severity?: "error" | "warning";
}

export interface ValidationResult {
  valid: boolean;
  profile: string;
  errors: ValidationError[];
}

/**
 * Thrown by an EditorRepository when createRecord/updateRecord is
 * rejected specifically because the record fails schema validation
 * (as opposed to a network failure, a 404, or a conflict). Kept
 * separate from repository-specific error classes so the editor can
 * react to it regardless of which EditorRepository is in use.
 */
export class RecordValidationError extends Error {
  constructor(
    message: string,
    public readonly errors: ValidationError[],
  ) {
    super(message);

    this.name = "RecordValidationError";
  }
}

export interface ReferenceListItem {
  id: string;
  name: string;
}

export interface TemplateField {
  path: string;
  value: unknown;
}

export interface Template {
  id: string;
  profile: string;
  name: string;
  fields: TemplateField[];
}

/**
 * "vl" and "cve-program" are both CVE Services API-shaped publish targets
 * (POST /cve-id, POST|PUT /cve/<id>/cna, POST|PUT /cve/<id>/reject) at a
 * different base URL/credentials — see the "CVE Program"/"Vulnerability-
 * Lookup" panels (editor/panels/publication/CnaPublicationPanel.vue).
 */
export type PublicationTarget = "vl" | "cve-program";

export interface CnaPublication {
  id: number;
  recordId: number;
  target: PublicationTarget;
  status: string;
  cveId: string | null;
  reservedAt: string | null;
  publishedAt: string | null;
  rejectedAt: string | null;
  lastError: string | null;
  createdAt: string;
  updatedAt: string;
}

// Scoring

export interface RecordQualityCheck {
  id: string;
  label: string;
  pillar: string;
  credit: number;
  weight: number;
  points: number;
  rule: string;
}

export interface RecordQualityPillar {
  id: string;
  label: string;
  points: number;
  maximum: number;
}

export interface RecordQualityScore {
  score: number;
  grade: string;
  methodologyVersion: number;
  pillars: RecordQualityPillar[];
  checks: RecordQualityCheck[];
}

export interface CpeVendorSuggestion {
  id: string;
  name: string;
  title?: string | null;
}

export interface CpeProductSuggestion {
  id: string;
  name: string;
  title?: string | null;
}

export interface CpeSearchParams {
  q?: string;
  vendorQ?: string;
  productQ?: string;
  part?: CpePart;
}

export type CpePart =
  | "a"
  | "o"
  | "h";

export interface CpeSuggestion {
  id: string;
  cpe: string;

  title?: string | null;
  part: CpePart;

  version: string;
  deprecated: boolean;
}

// Interfaces for patch2vuln
export interface Patch2VulnContext {
  vendor?: string;
  product?: string;
  affectedVersion?: string;
  fixedVersion?: string;
  versionType?: string;
}

export interface Patch2VulnInput {
  commitUrls: string[];
  files: File[];
  context: Patch2VulnContext;
}

export interface Patch2VulnResult {
  record: CveRecord;
  analysis: unknown;
}

export interface Patch2VulnJob {
  jobId: string;
  status: "queued" | "running" | "completed" | "failed";
  result?: Patch2VulnResult;
  error?: string;
}

// Jobs
export type BackgroundJobStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed";

export interface BackgroundJobEvent {
  jobId: string;
  status: BackgroundJobStatus;
}

export interface EditorRepository {
  loadRecord(
    identifier: string,
  ): Promise<LoadedRecord>;

  createRecord(
    record: EditorDocument,
    profile: string,
    isDraft: boolean,
  ): Promise<LoadedRecord>;

  updateRecord(
    identifier: string,
    record: EditorDocument,
    profile: string,
    isDraft: boolean,
  ): Promise<LoadedRecord>;

  validateRecord(
    record: EditorDocument,
    profile: string,
  ): Promise<ValidationResult>;

  deleteRecord?(
    identifier: string,
  ): Promise<void>;

  /**
   * Optional: a host may not have this data available (e.g. no
   * outbound access to MITRE from wherever it runs), in which case
   * cweId/capecId fields fall back to plain free-text entry — the
   * schema only ever required a pattern-matching string, never a
   * value drawn from this list, so nothing breaks by omitting it.
   */
  getReferenceList?(
    kind: "cwe" | "capec",
  ): Promise<ReferenceListItem[]>;

  searchCpeVendors?(
    q: string
  ): Promise<CpeVendorSuggestion[]>;

  searchCpeProducts?(
    q: string,
    vendorQ?: string,
  ): Promise<CpeProductSuggestion[]>;

  searchCpes?(
    params:  CpeSearchParams,
  ): Promise<CpeSuggestion[]>;

  /**
   * Optional: a host may have no place to persist templates (e.g.
   * no per-user storage at all), in which case the Templates
   * section shows a "not supported here" message instead of the
   * create/apply UI — nothing else in the editor depends on this.
   * Templates belong to the profile they were captured from (a CVE
   * path like containers.cna.affected.0.vendor makes no sense
   * offered against a differently-shaped profile), so listing/
   * creating both take the active profile explicitly rather than
   * returning/accepting every template regardless of shape.
   */
  listTemplates?(
    profile: string,
  ): Promise<Template[]>;

  saveTemplate?(
    profile: string,
    name: string,
    fields: TemplateField[],
  ): Promise<Template>;

  updateTemplate?(
    id: string,
    name: string,
    fields: TemplateField[],
  ): Promise<Template>;

  deleteTemplate?(
    id: string,
  ): Promise<void>;

  /**
   * Optional: a host may have no CNA-publication backend at all (e.g. no
   * outbound access it's willing to grant, or it does this some other
   * way), in which case the "Vulnerability-Lookup"/"CVE Program" panels
   * show a "not supported here" message instead of the publish UI. A
   * host that does implement these is expected to implement all five
   * together — the panels gate visibility on getCnaPublication alone,
   * the same way the Templates section gates on listTemplates alone.
   */
  getCnaPublication?(
    target: PublicationTarget,
    recordIdentifier: string,
  ): Promise<CnaPublication>;

  reserveCveId?(
    target: PublicationTarget,
    recordIdentifier: string,
    year: number,
  ): Promise<CnaPublication>;

  publishCna?(
    target: PublicationTarget,
    recordIdentifier: string,
  ): Promise<CnaPublication>;

  rejectCna?(
    target: PublicationTarget,
    recordIdentifier: string,
    reason: string,
  ): Promise<CnaPublication>;

  abortCna?(
    target: PublicationTarget,
    recordIdentifier: string,
  ): Promise<CnaPublication>;


  // Scoreboard
  scoreRecordQuality?(
    record: EditorDocument,
    profile: string,
  ): Promise<RecordQualityScore>;


  // patch2vuln
  submitPatch2VulnJob?(
    input: Patch2VulnInput,
  ): Promise<Patch2VulnJob>;

  getPatch2VulnJob?(
    jobId: string,
  ): Promise<Patch2VulnJob>;

  subscribeJobEvents?(
    jobId: string,
    onStatus: (event: BackgroundJobEvent) => void,
    onDisconnect?: () => void,
  ): () => void;

  /**
   * Optional: which draft/publish-style buttons the editor header
   * shows, and what each sets isDraft to when clicked. Absent means
   * "use the standalone app's own default pair" (see
   * editor/core/lifecycle.ts's DEFAULT_LIFECYCLE_TRANSITIONS); an
   * explicit [] means this host has no such concept at all (e.g.
   * vulnerability-lookup's CNA API persists immediately, with nowhere
   * to store an incomplete draft) and the editor shows none of these
   * buttons. Each entry's run cost is always the same —
   * controller.save(targetIsDraft) — so unlike EditorAction there is
   * no run() here, only what to call it with and when to show it.
   */
  lifecycleTransitions?: LifecycleTransition[];

}

export interface EditorContext {
  identifier: string | null;
  profile: string;
  record: EditorDocument;
  isDraft: boolean;
}

export interface LifecycleTransition {
  id: string;
  label: string;
  targetIsDraft: boolean;

  /**
   * Hide the button entirely for the current context. Defaults to
   * always visible — a host providing a single custom transition
   * presumably wants it shown unconditionally unless it says
   * otherwise.
   */
  isVisible?(context: EditorContext): boolean;
}

/**
 * An optional, host-supplied action shown as an extra button in the
 * editor header (e.g. "Publish to CVE Project"). Actions are entirely
 * host-configured, the same way an EditorRepository is: Vulniverse
 * ships a few built-ins under editor/actions/, but a host decides
 * which (if any) to pass in via VulniverseEditor's `actions` prop.
 */
export interface EditorAction {
  id: string;
  label: string;

  /**
   * Hide the button entirely for the current context. Defaults to
   * always visible.
   */
  isVisible?(context: EditorContext): boolean;

  /**
   * Show the button but disable it for the current context. Defaults
   * to always enabled.
   */
  isEnabled?(context: EditorContext): boolean;

  run(context: EditorContext): Promise<void>;
}

/**
 * An optional, host-supplied navigation tab + the component rendered
 * for it (e.g. a "CVE Project" panel showing publish status). Like
 * EditorAction, entirely host-configured via VulniverseEditor's
 * `panels` prop. The component receives the same EditorContext
 * as a single `context` prop — not via provide/inject — so it works
 * regardless of which bundle built it, exactly like EditorAction.run().
 */
export interface EditorPanel {
  id: string;
  label: string;
  component: Component;
  isVisible?(context: EditorContext): boolean;
}
