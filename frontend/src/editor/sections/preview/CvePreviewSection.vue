<script setup lang="ts">
import {
  computed,
} from "vue";

import {
  useEditorContext,
} from "../../core/context";

import {
  findXGcveOccurrences,
} from "../../gcve";

import MetadataPreview from
  "./MetadataPreview.vue";

import SourcePreview from
  "./SourcePreview.vue";

import GcvePreview from
  "./GcvePreview.vue";

import {
  formatDate,
  providerLabel,
} from "./utils";

import type {
  AnyRecord,
  PreviewDate,
  PreviewSource,
} from "./types";


const editor =
  useEditorContext();


const record =
  computed<AnyRecord>(() => {
    return (
      editor.record.value ?? {}
    ) as AnyRecord;
  });


const cveMetadata =
  computed<AnyRecord>(() => {
    return (
      record.value.cveMetadata as
        | AnyRecord
        | undefined
    ) ?? {};
  });


const isGcve =
  computed(() => {
    return (
      editor.profile.value
        ?.startsWith("gcve-")
      ?? false
    );
  });


const gcveOccurrences =
  computed(() => {
    return findXGcveOccurrences(
      record.value,
    );
  });


const gcveVulnId =
  computed(() => {
    return (
      gcveOccurrences.value[0]
        ?.extensions[0]
        ?.vulnId
    );
  });


const primaryIdentifier =
  computed(() => {
    const cveId =
      cveMetadata.value.cveId as
        | string
        | undefined;

    const vulnId =
      gcveVulnId.value
      ?? (
        cveMetadata.value.vulnId as
          | string
          | undefined
      );

    if (
      isGcve.value &&
      vulnId
    ) {
      return vulnId;
    }

    return (
      cveId
      ?? vulnId
      ?? "Unassigned identifier"
    );
  });


const secondaryIdentifier =
  computed(() => {
    const cveId =
      cveMetadata.value.cveId as
        | string
        | undefined;

    return (
      cveId &&
      cveId !==
        primaryIdentifier.value
    )
      ? cveId
      : undefined;
  });


const state =
  computed(() => {
    return (
      cveMetadata.value.state as
        | string
        | undefined
    );
  });


const METADATA_DATES = [
  {
    key: "dateReserved",
    label: "Reserved",
  },
  {
    key: "datePublished",
    label: "Published",
  },
  {
    key: "dateUpdated",
    label: "Updated",
  },
  {
    key: "dateRejected",
    label: "Rejected",
  },
] as const;


const metadataDates =
  computed<PreviewDate[]>(() => {
    return METADATA_DATES.flatMap(
      (entry) => {
        const value =
          formatDate(
            cveMetadata.value[
              entry.key
            ],
          );

        return value
          ? [{
              label:
                entry.label,
              value,
            }]
          : [];
      },
    );
  });


const assigner =
  computed(() => {
    return (
      cveMetadata.value
        .assignerShortName
      ?? cveMetadata.value
        .assignerOrgId
    ) as
      | string
      | undefined;
  });


const sources =
  computed<PreviewSource[]>(() => {
    const containers =
      (
        record.value
          .containers as
          | AnyRecord
          | undefined
      ) ?? {};

    const cna =
      (
        containers.cna as
          | AnyRecord
          | undefined
      ) ?? {};

    const adp =
      (
        containers.adp as
          | AnyRecord[]
          | undefined
      ) ?? [];

    return [
      {
        key: "cna",
        label:
          (
            cna.title as
              | string
              | undefined
          )
          ?? "Primary description",
        badge: "CNA",
        data: cna,
      },

      ...adp.map(
        (entry, index) => ({
          key: `adp-${index}`,
          label:
            (
              entry.title as
                | string
                | undefined
            )
            ?? providerLabel(
              entry,
            ),
          badge: "ADP",
          data: entry,
        }),
      ),
    ];
  });
</script>


<template>
  <section>
    <header class="mb-3">
      <h2 class="h4">
        Preview
      </h2>

      <p class="text-secondary">
        A read-only rendering of the
        record as currently edited.
      </p>
    </header>

    <MetadataPreview
      :primary-identifier="
        primaryIdentifier
      "
      :secondary-identifier="
        secondaryIdentifier
      "
      :state="state"
      :assigner="assigner"
      :dates="metadataDates"
    />

    <SourcePreview
      v-for="source in sources"
      :key="source.key"
      :source="source"
    />

    <GcvePreview
      :occurrences="
        gcveOccurrences
      "
    />
  </section>
</template>
