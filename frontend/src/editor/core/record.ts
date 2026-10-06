import type {
  LoadedRecord,
  VulnerabilityRecord,
} from "../contracts";

export function createEmptyRecord(
  profile: string,
): LoadedRecord {
  return {
    identifier: "",
    profile,
    isDraft: true,
    record: {
      dataType: "CVE_RECORD",
      dataVersion: "5.2.0",
      cveMetadata: {},
      containers: {
        cna: {
          descriptions: [],
          affected: [],
          references: [],
        },
      },
      ...(profile.startsWith("gcve-")
        ? { x_gcve: [] }
        : {}),
    },
  };
}

export function rejectRecord(
  source: VulnerabilityRecord,
  reason: string,
  rejectedAt = new Date().toISOString(),
): VulnerabilityRecord {
  const previousProviderMetadata =
    source.containers?.cna?.providerMetadata;

  return {
    ...source,

    cveMetadata: {
      ...source.cveMetadata,
      state: "REJECTED",
      dateRejected: rejectedAt,
      dateUpdated: rejectedAt,
    },

    containers: {
      ...source.containers,

      // A rejected CNA container has a different schema from a normal
      // CNA container, so replace it completely.
      cna: {
        providerMetadata: {
          ...previousProviderMetadata,
          dateUpdated: rejectedAt,
        },

        rejectedReasons: [
          {
            lang: "en",
            value: reason,
          },
        ],
      },
    },
  };
}

