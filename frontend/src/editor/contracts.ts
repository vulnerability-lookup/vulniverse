import type {
  Component,
} from "vue";

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
  vulnId: string;
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

export interface VulnerabilityRecord {
  dataType?: string;
  dataVersion?: string;
  cveMetadata?: CveMetadata;
  containers?: RecordContainers;
  x_gcve?: GcveExtension[];

  /*
   * Records may contain extensions that Vulniverse does not
   * currently render. Those must remain in the object.
   */
  [key: string]: unknown;
}

export interface LoadedRecord {
  identifier: string;
  profile: string;
  record: VulnerabilityRecord;
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
  name: string;
  fields: TemplateField[];
}

export interface EditorRepository {
  loadRecord(
    identifier: string,
  ): Promise<LoadedRecord>;

  createRecord(
    record: VulnerabilityRecord,
    profile: string,
    isDraft: boolean,
  ): Promise<LoadedRecord>;

  updateRecord(
    identifier: string,
    record: VulnerabilityRecord,
    profile: string,
    isDraft: boolean,
  ): Promise<LoadedRecord>;

  validateRecord(
    record: VulnerabilityRecord,
    profile: string,
  ): Promise<ValidationResult>;

  deleteRecord(
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

  /**
   * Optional: a host may have no place to persist templates (e.g.
   * no per-user storage at all), in which case the Templates
   * section shows a "not supported here" message instead of the
   * create/apply UI — nothing else in the editor depends on this.
   */
  listTemplates?(): Promise<Template[]>;

  saveTemplate?(
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
}

export interface EditorModuleContext {
  identifier: string | null;
  profile: string;
  record: VulnerabilityRecord;
  isDraft: boolean;
}

/**
 * An optional, host-supplied action shown as an extra button in the
 * editor header (e.g. "Publish to CVE Project"). Modules are entirely
 * host-configured, the same way an EditorRepository is: Vulniverse
 * ships a few built-ins under editor/modules/, but a host decides
 * which (if any) to pass in via VulniverseEditor's `modules` prop.
 */
export interface EditorModule {
  id: string;
  label: string;

  /**
   * Hide the button entirely for the current context. Defaults to
   * always visible.
   */
  isVisible?(context: EditorModuleContext): boolean;

  /**
   * Show the button but disable it for the current context. Defaults
   * to always enabled.
   */
  isEnabled?(context: EditorModuleContext): boolean;

  run(context: EditorModuleContext): Promise<void>;
}

/**
 * An optional, host-supplied navigation tab + the component rendered
 * for it (e.g. a "CVE Project" panel showing publish status). Like
 * EditorModule, entirely host-configured via VulniverseEditor's
 * `panels` prop. The component receives the same EditorModuleContext
 * as a single `context` prop — not via provide/inject — so it works
 * regardless of which bundle built it, exactly like EditorModule.run().
 */
export interface EditorPanel {
  id: string;
  label: string;
  component: Component;
  isVisible?(context: EditorModuleContext): boolean;
}
