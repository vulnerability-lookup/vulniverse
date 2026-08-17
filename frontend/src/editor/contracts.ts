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

export interface CnaContainer {
  descriptions?: Description[];
  affected?: unknown[];
  references?: unknown[];

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
}
