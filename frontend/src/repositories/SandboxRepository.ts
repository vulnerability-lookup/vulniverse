import type {
  EditorRepository,
  LoadedRecord,
  ValidationResult,
  VulnerabilityRecord,
  ReferenceListItem,
} from "@/editor/contracts";

// import {
//   apiRequest,
// } from "./apiRequest";

import {
  EditorRepositoryError,
} from "@/editor/core/errors";

const SANDBOX_IDENTIFIER = "sandbox";

/**
 * Deep-clones a record into a genuinely plain object graph — mirrors
 * what a real network round-trip does
 */
function cloneRecord(record: VulnerabilityRecord): VulnerabilityRecord {
  return JSON.parse(JSON.stringify(record)) as VulnerabilityRecord;
}

/**
 * An EditorRepository with no backend storage at all — everything
 * lives in memory for the lifetime of the page, gone on refresh.
 */
export class SandboxRepository implements EditorRepository {
  private record: VulnerabilityRecord | null = null;
  private profile = "cve-5.2.0";
  private isDraft = true;

  async loadRecord(
    identifier: string,
  ): Promise<LoadedRecord> {
    if (identifier !== SANDBOX_IDENTIFIER || !this.record) {
      throw new EditorRepositoryError("No sandbox record yet.", 404);
    }

    return this.toLoadedRecord();
  }

  async createRecord(
    record: VulnerabilityRecord,
    profile: string,
    isDraft: boolean,
  ): Promise<LoadedRecord> {
    this.record = cloneRecord(record);
    this.profile = profile;
    this.isDraft = isDraft;

    return this.toLoadedRecord();
  }

  async updateRecord(
    _identifier: string,
    record: VulnerabilityRecord,
    profile: string,
    isDraft: boolean,
  ): Promise<LoadedRecord> {
    this.record = cloneRecord(record);
    this.profile = profile;
    this.isDraft = isDraft;

    return this.toLoadedRecord();
  }

  /**
  * validate Record works as it is stateless
  **/
  // async validateRecord(
  //   record: VulnerabilityRecord,
  //   profile: string,
  // ): Promise<ValidationResult> {
  //   return apiRequest<ValidationResult>(
  //     "/validate",
  //     {
  //       method: "POST",
  //       body: JSON.stringify({ record, profile }),
  //     },
  //   );
  // }

  async validateRecord(
    _record: VulnerabilityRecord,
    _profile: string,
  ): Promise<ValidationResult> {
    throw new EditorRepositoryError(
      "Validation is not available in demo mode.",
      501,
    );
  }

  // async deleteRecord(): Promise<void> {
  //   this.record = null;
  // }

  private toLoadedRecord(): LoadedRecord {
    return {
      identifier: SANDBOX_IDENTIFIER,
      profile: this.profile,
      record: this.record ?? {},
      isDraft: this.isDraft,
    };
  }

  async getReferenceList(
    kind: "cwe" | "capec",
  ): Promise<ReferenceListItem[]> {
    const response = await fetch(
      `${import.meta.env.BASE_URL}data/references/${kind}.json`,
    );

    if (!response.ok) {
      throw new EditorRepositoryError(
        `Failed to load ${kind.toUpperCase()} reference data.`,
        response.status,
      );
    }

    const result = await response.json() as {
      items: ReferenceListItem[];
    };

    return result.items;
  }


}
