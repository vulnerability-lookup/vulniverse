import type {
  CnaPublication,
  CveRecord,
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
  CpeProductSuggestion,
  CpeSearchParams,
  Patch2VulnContext,
  Patch2VulnJob,
  Patch2VulnInput,
  Patch2VulnResult,
  BackgroundJobEvent,
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
  id: number;
  /** The CVE/GCVE/OSV identifier; null for a draft without one yet. */
  identifier: string | null;
  profile: string;
  isDraft: boolean;
  updatedAt: string;
  createdBy: string | null;
  organisation: { id: number; name: string };
}

/*
 * Patch2Vuln batches (pages/Patch2Vuln*.vue): app-level too, the
 * embeddable element only ever sees one record.
 */
export interface Patch2VulnBatchSummary {
  id: number;
  name: string;
  profile: string;
  createdAt: string;
  createdBy: string | null;
  total: number;
  /** Queued or running. */
  open: number;
  completed: number;
  /** Turned into a record, or dismissed. */
  reviewed: number;
}

export type CandidateStatus =
  | "queued" | "running" | "completed" | "failed" | "canceled" | "expired";

export interface Patch2VulnCandidate {
  id: number;
  commitUrls: string[];
  status: CandidateStatus;
  title: string | null;
  dismissed: boolean;
  recordId: number | null;
}

export interface Patch2VulnBatch extends Patch2VulnBatchSummary {
  candidates: Patch2VulnCandidate[];
  /** Patch2Vuln couldn't be reached; statuses are the last known ones. */
  refreshError: string | null;
}

export interface Patch2VulnCandidateResult extends Patch2VulnCandidate {
  batchId: number;
  profile: string;
  result: Patch2VulnResult;
}

/** The backend addresses records by database id; the editor contract
 * calls that opaque key `identifier` and shows `vulnerabilityId`. */
interface RecordResponse {
  id: number;
  identifier: string | null;
  profile: string;
  record: EditorDocument;
  isDraft: boolean;
  /** Counts saves; sent back with the next save (see `versions`). */
  version: number;
}

function toLoadedRecord(response: RecordResponse): LoadedRecord {
  return {
    identifier: String(response.id),
    vulnerabilityId: response.identifier,
    profile: response.profile,
    record: response.record,
    isDraft: response.isDraft,
  };
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
  features: SuggestionFeatures;
}

export interface SuggestionFeatures {
  cpeVendors: boolean;
  cpeProducts: boolean;
  cpeEntries: boolean;
  cwe: boolean;
  capec: boolean;
}

const CLOSED_SUGGESTION_FEATURES: SuggestionFeatures = {
  cpeVendors: false,
  cpeProducts: false,
  cpeEntries: false,
  cwe: false,
  capec: false,
};

// Used by both getCapabilities() (parsing the raw API response) and
// setFeatures() (accepting that same shape back from a caller) — a
// malformed/partial object normalizes to "closed" per key rather than
// throwing or leaving a key undefined.
function normalizeSuggestionFeatures(
  features: Partial<SuggestionFeatures> | undefined,
): SuggestionFeatures {
  return {
    cpeVendors: features?.cpeVendors === true,
    cpeProducts: features?.cpeProducts === true,
    cpeEntries: features?.cpeEntries === true,
    cwe: features?.cwe === true,
    capec: features?.capec === true,
  };
}


// CPE stuff

interface CpeVendorApiItem {
  id: number;
  uuid: string;
  name: string;
  title: string | null;
}


interface CpeProductApiItem {
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
  private suggestionFeatures: SuggestionFeatures = {
    ...CLOSED_SUGGESTION_FEATURES,
  };

  /*
   * The version of each record as last loaded or saved here, sent with
   * its next save: the backend refuses a save based on an outdated copy
   * (someone else saved in between) instead of overwriting their work.
   * Kept here, not in the editor contract, so hosts with their own
   * repositories (Vulnerability-Lookup) are unaffected.
   */
  private readonly versions = new Map<string, number>();

  /*
   * The Patch2Vuln candidate the next new record is created from: sent
   * with that createRecord, so the backend links the two.
   */
  candidateId: number | null = null;

  constructor(
    private readonly apiRoot = "/api/v1",
  ) { }

  private remember(response: RecordResponse): LoadedRecord {
    this.versions.set(String(response.id), response.version);

    return toLoadedRecord(response);
  }

  async listRecords(): Promise<RecordSummary[]> {
    const result = await this.request<{ records: RecordSummary[] }>(
      "/records",
    );

    return result.records;
  }

  async listPatch2VulnBatches(): Promise<Patch2VulnBatchSummary[]> {
    return (await this.request<{ batches: Patch2VulnBatchSummary[] }>(
      "/patch2vuln/batches",
    )).batches;
  }

  /** `commitUrls`: one list of commit URLs per vulnerability.
   * `context`: the panel's optional fields, for every vulnerability. */
  createPatch2VulnBatch(
    name: string,
    profile: string,
    commitUrls: string[][],
    context: Patch2VulnContext = {},
  ): Promise<Patch2VulnBatchSummary> {
    return this.request("/patch2vuln/batches", {
      method: "POST",
      body: JSON.stringify({ name, profile, commitUrls, context }),
    });
  }

  getPatch2VulnBatch(id: number): Promise<Patch2VulnBatch> {
    return this.request(`/patch2vuln/batches/${id}`);
  }

  async deletePatch2VulnBatch(id: number): Promise<void> {
    await this.request(`/patch2vuln/batches/${id}`, { method: "DELETE" });
  }

  getPatch2VulnCandidate(id: number): Promise<Patch2VulnCandidateResult> {
    return this.request(`/patch2vuln/candidates/${id}`);
  }

  setPatch2VulnCandidateDismissed(
    id: number,
    dismissed: boolean,
  ): Promise<Patch2VulnCandidate> {
    return this.request(`/patch2vuln/candidates/${id}/dismiss`, {
      method: "POST",
      body: JSON.stringify({ dismissed }),
    });
  }

  async getCapabilities(): Promise<AppCapabilities> {
    const result = await this.request<{
      panels?: Record<string, boolean>;
      actions?: Record<string, boolean>;
      features?: Partial<SuggestionFeatures>;
    }>("/capabilities");

    return {
      panels: result.panels ?? {},
      actions: result.actions ?? {},
      features: normalizeSuggestionFeatures(result.features),
    };
  }

  /*
   * Called explicitly by the standalone app's pages once
   * getCapabilities() resolves (see EditorPage.vue/NewRecordPage.vue)
   * — kept separate from getCapabilities() itself so that method
   * stays a pure fetch rather than one with a side effect a reader
   * wouldn't expect from its name. Until this is called, every
   * suggestion lookup below stays closed (see the constructor), so a
   * page that never calls it just never gets suggestions rather than
   * getting them unconditionally.
   */
  setFeatures(
    features: Partial<SuggestionFeatures> | undefined,
  ): void {
    this.suggestionFeatures = normalizeSuggestionFeatures(features);
  }

  async loadRecord(
    identifier: string,
  ): Promise<LoadedRecord> {
    return this.remember(await this.request<RecordResponse>(
      `/records/${encodeURIComponent(identifier)}`,
    ));
  }

  async createRecord(
    record: EditorDocument,
    profile: string,
    isDraft: boolean,
  ): Promise<LoadedRecord> {
    const saved = this.remember(await this.request<RecordResponse>(
      "/records",
      {
        method: "POST",
        body: JSON.stringify({
          record,
          profile,
          isDraft,
          ...(this.candidateId === null ? {} : { candidateId: this.candidateId }),
        }),
      },
    ));

    // Linked now; later records from this page are unrelated.
    this.candidateId = null;

    return saved;
  }

  async updateRecord(
    identifier: string,
    record: EditorDocument,
    profile: string,
    isDraft: boolean,
  ): Promise<LoadedRecord> {
    return this.remember(await this.request<RecordResponse>(
      `/records/${encodeURIComponent(identifier)}`,
      {
        method: "PUT",
        body: JSON.stringify({
          record,
          profile,
          isDraft,
          // Absent for a record not loaded here; JSON drops undefined.
          version: this.versions.get(identifier),
        }),
      },
    ));
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


  async submitPatch2VulnJob(
    input: Patch2VulnInput,
  ): Promise<Patch2VulnJob> {
    const formData = new FormData();

    formData.append(
      "commitUrls",
      JSON.stringify(input.commitUrls),
    );

    for (const file of input.files) {
      formData.append("files", file);
    }

    for (const [key, value] of Object.entries(input.context)) {
      if (value) {
        formData.append(key, value);
      }
    }

    return this.request<Patch2VulnJob>(
      "/patch2vuln/jobs",
      {
        method: "POST",
        body: formData,
      },
    );
  }

  async getPatch2VulnJob(
    jobId: string,
  ): Promise<Patch2VulnJob> {
    return this.request<Patch2VulnJob>(
      `/patch2vuln/jobs/${encodeURIComponent(jobId)}`,
    );
  }

  async cancelPatch2VulnJob(
    jobId: string,
  ): Promise<Patch2VulnJob> {
    return this.request<Patch2VulnJob>(
      `/patch2vuln/jobs/${encodeURIComponent(jobId)}`,
      { method: "DELETE" },
    );
  }

  async getReferenceList(
    kind: "cwe" | "capec",
  ): Promise<ReferenceListItem[]> {
    if (!this.suggestionFeatures[kind]) {
      return [];
    }

    const result = await this.request<{ items: ReferenceListItem[] }>(
      `/references/${kind}`,
    );

    return result.items;
  }

  async searchCpeVendors(
    q: string,
  ): Promise<CpeVendorSuggestion[]> {
    if (!this.suggestionFeatures.cpeVendors) {
      return [];
    }

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

  async searchCpeProducts(
    q: string,
    vendorQ?: string,
  ): Promise<CpeProductSuggestion[]> {
    if (!this.suggestionFeatures.cpeProducts) {
      return [];
    }

    const query =
      new URLSearchParams({
        q,
      });

    if (vendorQ) {
      query.set(
        "vendor_q",
        vendorQ,
      );
    }

    const response = await this.request<
      | CpeProductApiItem[]
      | CpeSearchApiResponse<CpeProductApiItem>
    >(
      `/cpe/products?${query.toString()}`,
    );

    return cpeSearchItems(
      response,
    ).map(
      (product) => ({
        id: product.uuid,

        name: product.name,

        title:
          product.title,
      }),
    );
  }

  async searchCpes(
    params: CpeSearchParams,
  ): Promise<CpeSuggestion[]> {
    if (!this.suggestionFeatures.cpeEntries) {
      return [];
    }

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
      {
        method: "POST",
        // The version this editor shows: the backend refuses to publish
        // if the stored record is another one (see updateRecord).
        body: JSON.stringify({ version: this.versions.get(recordIdentifier) }),
      },
    );
  }

  async getUpstreamCna(
    target: PublicationTarget,
    recordIdentifier: string,
  ): Promise<CveRecord> {
    const { record } = await this.request<{ record: CveRecord }>(
      `/publish/${target}/${encodeURIComponent(recordIdentifier)}/upstream`,
    );
    return record;
  }

  async unlinkCna(
    target: PublicationTarget,
    recordIdentifier: string,
  ): Promise<CnaPublication> {
    return this.request<CnaPublication>(
      `/publish/${target}/${encodeURIComponent(recordIdentifier)}`,
      { method: "DELETE" },
    );
  }

  async pullCna(
    target: PublicationTarget,
    recordIdentifier: string,
    cveId: string,
  ): Promise<{ publication: CnaPublication; record: CveRecord | null }> {
    return this.request(
      `/publish/${target}/${encodeURIComponent(recordIdentifier)}/pull`,
      {
        method: "POST",
        body: JSON.stringify({ cveId }),
      },
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

  subscribeJobEvents(
    jobId: string,
    onStatus: (event: BackgroundJobEvent) => void,
    onDisconnect?: () => void,
  ): () => void {

    const url = `${this.apiRoot}/patch2vuln/jobs/${encodeURIComponent(jobId)}/events`;

    const source = new EventSource(url, {
      withCredentials: true,
    });

    const handleStatus = (event: Event): void => {
      try {
        const message = event as MessageEvent<string>;

        const data = JSON.parse(
          message.data,
        ) as BackgroundJobEvent;

        if (data.jobId !== jobId) {
          return;
        }

        onStatus(data);

      } catch (err) {
        console.error(
          "Invalid job SSE event:",
          err,
        );
      }
    };

    source.addEventListener("status", handleStatus);

    source.onerror = () => {
      // EventSource automatically reconnects after
      // a temporary connection failure.
      onDisconnect?.();
    };

    return () => {
      source.removeEventListener("status", handleStatus);
      source.close();
    };
  }


}
