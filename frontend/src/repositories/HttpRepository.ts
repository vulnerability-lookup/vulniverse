import type {
  EditorRepository,
  LoadedRecord,
  ReferenceListItem,
  ValidationResult,
  VulnerabilityRecord,
} from "@/editor/contracts";

import {
  RecordValidationError,
} from "@/editor/contracts";

import {
  RepositoryError,
} from "./RepositoryError";

/*
 * Not part of EditorRepository: listing records is a standalone-app
 * concern (the home page), not something the embeddable
 * <vulniverse-editor> element itself ever needs.
 */
export interface RecordSummary {
  identifier: string;
  profile: string;
  isDraft: boolean;
  updatedAt: string;
}

export class HttpRepository
  implements EditorRepository
{
  constructor(
    private readonly apiRoot = "/api/v1",
  ) {}

  async listRecords(): Promise<RecordSummary[]> {
    const result = await this.request<{ records: RecordSummary[] }>(
      "/records",
    );

    return result.records;
  }

  async loadRecord(
    identifier: string,
  ): Promise<LoadedRecord> {
    return this.request<LoadedRecord>(
      `/records/${encodeURIComponent(identifier)}`,
    );
  }

  async createRecord(
    record: VulnerabilityRecord,
    profile: string,
    isDraft: boolean,
  ): Promise<LoadedRecord> {
    return this.request<LoadedRecord>(
      "/records",
      {
        method: "POST",
        body: JSON.stringify({
          record,
          profile,
          isDraft,
        }),
      },
    );
  }

  async updateRecord(
    identifier: string,
    record: VulnerabilityRecord,
    profile: string,
    isDraft: boolean,
  ): Promise<LoadedRecord> {
    return this.request<LoadedRecord>(
      `/records/${encodeURIComponent(identifier)}`,
      {
        method: "PUT",
        body: JSON.stringify({
          record,
          profile,
          isDraft,
        }),
      },
    );
  }

  async validateRecord(
    record: VulnerabilityRecord,
    profile: string,
  ): Promise<ValidationResult> {
    return this.request<ValidationResult>(
      "/validate",
      {
        method: "POST",
        body: JSON.stringify({
          record,
          profile,
        }),
      },
    );
  }

  async deleteRecord(
    identifier: string,
  ): Promise<void> {
    await this.request<unknown>(
      `/records/${encodeURIComponent(identifier)}`,
      { method: "DELETE" },
    );
  }

  async getReferenceList(
    kind: "cwe" | "capec",
  ): Promise<ReferenceListItem[]> {
    const result = await this.request<{ items: ReferenceListItem[] }>(
      `/references/${kind}`,
    );

    return result.items;
  }

  private async request<T>(
    path: string,
    init: RequestInit = {},
  ): Promise<T> {
    const headers = new Headers(init.headers);

    headers.set("Accept", "application/json");

    if (init.body !== undefined) {
      headers.set(
        "Content-Type",
        "application/json",
      );
    }

    const response = await fetch(
      `${this.apiRoot}${path}`,
      {
        ...init,
        headers,
        credentials: "same-origin",
      },
    );

    const body = await response
      .json()
      .catch(() => null);

    if (!response.ok) {
      if (
        response.status === 422 &&
        Array.isArray(body?.errors)
      ) {
        throw new RecordValidationError(
          body.message ?? "The record is not publishable.",
          body.errors,
        );
      }

      throw new RepositoryError(
        body?.message ??
          `${response.status} ${response.statusText}`,
        response.status,
        body,
      );
    }

    return body as T;
  }
}
