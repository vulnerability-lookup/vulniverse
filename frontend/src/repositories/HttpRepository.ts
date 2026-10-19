import type {
  CnaPublication,
  EditorDocument,
  EditorRepository,
  LoadedRecord,
  PublicationTarget,
  ReferenceListItem,
  Template,
  TemplateField,
  ValidationResult,
  CpeSuggestion,
  CpeVendorSuggestion,
  CpeSearchParams,
} from "@/editor/contracts";

import {
  RecordValidationError,
} from "@/editor/contracts";

import {
  EditorRepositoryError,
} from "@/editor/core/errors";

import {
  ApiError,
} from "@/shared/errors";

import {
  apiRequest,
} from "./apiRequest";

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
  createdBy: string | null;
}

/*
 * Not part of EditorRepository either: which panels/actions the
 * standalone app shows is a deployment-config concern
 * (config/vulniverse.toml), not something an embedding host needs —
 * a host authors its own panels/actions directly, see
 * editor/panels/index.ts and editor/actions/index.ts.
 */
export interface AppCapabilities {
  panels: Record<string, boolean>;
  actions: Record<string, boolean>;
}


// CPE stuff

interface CpeVendorApiItem {
  id: number;
  uuid: string;
  name: string;
  title: string | null;
}


interface CpeApiItem {
  id: number;
  cpe_name_id: string;
  cpe_uri: string;

  title: string | null;

  part: string;
  version: string;

  deprecated: boolean;
  deprecated_by: string | null;

  vendor_id: number;
  vendor_uuid: string;

  product_id: number;
  product_uuid: string;
}


interface CpeSearchApiResponse<T> {
  items: T[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

/*
 * The backend deliberately returns [] when a search term is too
 * short, while normal upstream search responses are paginated
 * objects containing `items`.
 */
function cpeSearchItems<T>(
  response:
    | T[]
    | CpeSearchApiResponse<T>,
): T[] {
  return Array.isArray(response)
    ? response
    : response.items;
}


function cpePart(
  value: string,
): CpeSuggestion["part"] | undefined {
  switch (value) {
    case "a":
    case "o":
    case "h":
      return value;

    default:
      return undefined;
  }
}

export class HttpRepository
  implements EditorRepository {
  constructor(
    private readonly apiRoot = "/api/v1",
  ) { }

  async listRecords(): Promise<RecordSummary[]> {
    const result = await this.request<{ records: RecordSummary[] }>(
      "/records",
    );

    return result.records;
  }

  async getCapabilities(): Promise<AppCapabilities> {
    const result = await this.request<{
      panels?: Record<string, boolean>;
      actions?: Record<string, boolean>;
    }>("/capabilities");

    return {
      panels: result.panels ?? {},
      actions: result.actions ?? {},
    };
  }

  async loadRecord(
    identifier: string,
  ): Promise<LoadedRecord> {
    return this.request<LoadedRecord>(
      `/records/${encodeURIComponent(identifier)}`,
    );
  }

  async createRecord(
    record: EditorDocument,
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
    record: EditorDocument,
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
    record: EditorDocument,
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

  async searchCpeVendors(
    q: string,
  ): Promise<CpeVendorSuggestion[]> {
    const query =
      new URLSearchParams({
        q,
      });

    const response = await this.request<
      | CpeVendorApiItem[]
      | CpeSearchApiResponse<CpeVendorApiItem>
    >(
      `/cpe/vendors?${query.toString()}`,
    );

    return cpeSearchItems(
      response,
    ).map(
      (vendor) => ({
        id: vendor.uuid,

        name: vendor.name,

        title:
          vendor.title,
      }),
    );
  }

  async searchCpes(
    params: CpeSearchParams,
  ): Promise<CpeSuggestion[]> {
    const query =
      new URLSearchParams();

    if (params.q) {
      query.set(
        "q",
        params.q,
      );
    }

    if (params.vendorQ) {
      query.set(
        "vendor_q",
        params.vendorQ,
      );
    }

    if (params.productQ) {
      query.set(
        "product_q",
        params.productQ,
      );
    }

    if (params.part) {
      query.set(
        "part",
        params.part,
      );
    }

    const response = await this.request<
      | CpeApiItem[]
      | CpeSearchApiResponse<CpeApiItem>
    >(
      `/cpe/cpes?${query.toString()}`,
    );

    return cpeSearchItems(
      response,
    ).flatMap(
      (item): CpeSuggestion[] => {
        const part =
          cpePart(
            item.part,
          );

        /*
         * Ignore malformed upstream entries rather
         * than exposing invalid suggestions.
         */
        if (!part) {
          return [];
        }

        return [{
          id:
            item.cpe_name_id,

          cpe:
            item.cpe_uri,

          title:
            item.title,

          part,

          version:
            item.version,

          deprecated:
            item.deprecated,
        }];
      },
    );
  }


  async listTemplates(
    profile: string,
  ): Promise<Template[]> {
    const result = await this.request<{
      templates: Array<{ id: number; profile: string; name: string; fields: TemplateField[] }>;
    }>(`/templates?profile=${encodeURIComponent(profile)}`);

    return result.templates.map((template) => ({
      ...template,
      id: String(template.id),
    }));
  }

  async saveTemplate(
    profile: string,
    name: string,
    fields: TemplateField[],
  ): Promise<Template> {
    const result = await this.request<{ id: number; profile: string; name: string; fields: TemplateField[] }>(
      "/templates",
      {
        method: "POST",
        body: JSON.stringify({ profile, name, fields }),
      },
    );

    return { ...result, id: String(result.id) };
  }

  async updateTemplate(
    id: string,
    name: string,
    fields: TemplateField[],
  ): Promise<Template> {
    const result = await this.request<{ id: number; profile: string; name: string; fields: TemplateField[] }>(
      `/templates/${encodeURIComponent(id)}`,
      {
        method: "PUT",
        body: JSON.stringify({ name, fields }),
      },
    );

    return { ...result, id: String(result.id) };
  }

  async deleteTemplate(
    id: string,
  ): Promise<void> {
    await this.request<unknown>(
      `/templates/${encodeURIComponent(id)}`,
      { method: "DELETE" },
    );
  }

  async getCnaPublication(
    target: PublicationTarget,
    recordIdentifier: string,
  ): Promise<CnaPublication> {
    return this.request<CnaPublication>(
      `/publish/${target}/${encodeURIComponent(recordIdentifier)}`,
    );
  }

  async reserveCveId(
    target: PublicationTarget,
    recordIdentifier: string,
    year: number,
  ): Promise<CnaPublication> {
    return this.request<CnaPublication>(
      `/publish/${target}/${encodeURIComponent(recordIdentifier)}/reserve`,
      {
        method: "POST",
        body: JSON.stringify({ year }),
      },
    );
  }

  async publishCna(
    target: PublicationTarget,
    recordIdentifier: string,
  ): Promise<CnaPublication> {
    return this.request<CnaPublication>(
      `/publish/${target}/${encodeURIComponent(recordIdentifier)}/publish`,
      { method: "POST" },
    );
  }

  async rejectCna(
    target: PublicationTarget,
    recordIdentifier: string,
    reason: string,
  ): Promise<CnaPublication> {
    return this.request<CnaPublication>(
      `/publish/${target}/${encodeURIComponent(recordIdentifier)}/reject`,
      {
        method: "POST",
        body: JSON.stringify({ reason }),
      },
    );
  }

  async abortCna(
    target: PublicationTarget,
    recordIdentifier: string,
  ): Promise<CnaPublication> {
    return this.request<CnaPublication>(
      `/publish/${target}/${encodeURIComponent(recordIdentifier)}/abort`,
      { method: "POST" },
    );
  }

  /*
   * The translation boundary between the generic HTTP world and the
   * EditorRepository abstraction: apiRequest() only knows about
   * HTTP/API semantics and throws ApiError, never anything
   * editor-specific. This wrapper is the one place that interprets an
   * ApiError for this particular API shape — a 422 with a body.errors
   * array means the record failed schema validation (RecordValidationError,
   * an EditorRepository-contract concept, see contracts.ts), anything
   * else becomes a generic EditorRepositoryError — so every other
   * EditorRepository method above can stay oblivious to HTTP entirely.
   */
  private async request<T>(
    path: string,
    init: RequestInit = {},
  ): Promise<T> {
    try {
      return await apiRequest<T>(path, init, this.apiRoot);
    } catch (error) {
      if (!(error instanceof ApiError)) {
        throw error;
      }

      const body = error.details as
        | { message?: string; errors?: unknown }
        | null
        | undefined;

      if (
        error.status === 422 &&
        Array.isArray(body?.errors)
      ) {
        throw new RecordValidationError(
          body?.message ?? "The record is not publishable.",
          body.errors,
        );
      }

      throw new EditorRepositoryError(
        error.message,
        error.status,
        error.details,
      );
    }
  }
}
