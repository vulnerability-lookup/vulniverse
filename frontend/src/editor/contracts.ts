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

export type ConversionTarget = "csaf" | "osv";

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
  // Shown to the model, so it can change the analysis.
  packageUrl?: string;
  // Only fills in the OSV output's package ecosystem.
  osvEcosystem?: string;
}

export interface Patch2VulnInput {
  commitUrls: string[];
  files: File[];
  context: Patch2VulnContext;
}

export interface Patch2VulnResult {
  record: CveRecord;
  // The same analysis as an OSV record, for OSV profiles.
  osv?: EditorDocument | null;
  // And as a CSAF 2.1 advisory (converted by the backend), for CSAF.
  csaf?: EditorDocument | null;
  analysis: unknown;
}

export interface Patch2VulnJob {
  jobId: string;
  status: BackgroundJobStatus;
  // false while queued/running: patch2vuln has no worker processing jobs.
  workerAvailable?: boolean;
  result?: Patch2VulnResult;
  error?: string;
}

// Jobs
export type BackgroundJobStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "canceled";

export interface BackgroundJobEvent {
  jobId: string;
  // null only with expired, when the server never reached the job's host.
  status: BackgroundJobStatus | null;
  workerAvailable?: boolean;
  // The server ended the stream before the job finished; poll instead
  // of reconnecting.
  expired?: boolean;
  // The job's host can't be reached: status is the last one known (or
  // null) and stays unknown until an event without this flag.
  unreachable?: boolean;
  error?: string;
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

  /**
   * Optional: a CSAF 2.1 or OSV 1.9.2 draft built from a CVE/GCVE record
   * (the "Convert to…" action). Converts only; nothing is saved. OSV
   * uses `ecosystem` for products without a package URL.
   */
  convertRecord?(
    record: EditorDocument,
    profile: string,
    target: ConversionTarget,
    options?: { ecosystem?: string },
  ): Promise<{ record: EditorDocument; profile: string }>;

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

  // A queued job is canceled at once; a running one reports "running"
  // until its worker stops, then "canceled" through the job's status.
  cancelPatch2VulnJob?(
    jobId: string,
  ): Promise<Patch2VulnJob>;

  subscribeJobEvents?(
    jobId: string,
    onStatus: (event: BackgroundJobEvent) => void,
    onDisconnect?: () => void,
  ): () => void;

  /**
   * Optional: which lifecycle buttons (Publish, Revert to draft, a
   * profile's Reject or Release, …) the editor header shows.
   *
   * - Absent: the default Publish/Revert pair plus the active
   *   profile's own transitions (editor/core/lifecycle.ts).
   * - An array: these instead of the default pair; the profile's own
   *   transitions are still added. An explicit [] means this host has
   *   no draft concept (e.g. vulnerability-lookup's CNA API persists
   *   immediately, with nowhere to store an incomplete draft): no
   *   Publish/Revert, but e.g. a CVE profile's Reject remains.
   * - A function: receives the defaults plus the profile's transitions
   *   and returns the list to use, to filter or extend them.
   */
  lifecycleTransitions?:
    | LifecycleTransition[]
    | ((transitions: LifecycleTransition[]) => LifecycleTransition[]);

}

export interface EditorContext {
  identifier: string | null;
  profile: string;
  record: EditorDocument;
  isDraft: boolean;
}

/**
 * One lifecycle step: a header button that saves the record with
 * isDraft set to targetIsDraft. A step may first ask for input (dialog)
 * and change the document (apply); the changed document only replaces
 * the editor's one once the save succeeded, so a step rejected by
 * validation leaves the editor as it was.
 */
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

  /**
   * Asks for the input apply() needs, e.g. a rejection reason. A
   * component exposing TransitionDialog.open().
   */
  dialog?: Component;

  /**
   * The document to save: gets a copy of the current one, the dialog's
   * input (undefined without a dialog) and one timestamp for every
   * date the step sets. Must not have side effects.
   */
  apply?(
    record: EditorDocument,
    input: unknown,
    now: string,
  ): EditorDocument;

  /** Shown after a successful save instead of the default notice. */
  notice?: string;

  /** Button style; defaults to a neutral outline button. */
  tone?: "success" | "warning" | "danger";
}

/**
 * What a LifecycleTransition's dialog component exposes: open() shows
 * it and resolves with the input, or with null when cancelled.
 */
export interface TransitionDialog {
  open(context: EditorContext): Promise<unknown>;
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

  /**
   * Asks for the input run() needs before it runs, like a lifecycle
   * transition's dialog (TransitionDialog: open() resolves with the
   * input, or null when cancelled).
   */
  dialog?: Component;

  run(context: EditorContext, input?: unknown): Promise<void>;
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
