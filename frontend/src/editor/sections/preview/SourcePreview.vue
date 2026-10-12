<script setup lang="ts">
import SupportingMediaPreview from
  "./SupportingMediaPreview.vue";

import type {
  SupportingMediaItem,
} from "./supporting-media";

import type {
  AnyRecord,
  PreviewSource,
} from "./types";

import {
  formatDate,
  formatValue,
  formatValueJson,
  isComplexValue,
} from "./utils";


defineProps<{
  source: PreviewSource;
}>();


function sourceDatesOf(
  source: AnyRecord,
): Array<{
  label: string;
  value: string;
}> {
  const entries: Array<{
    label: string;
    value: string;
  }> = [];

  const assigned =
    formatDate(
      source.dateAssigned,
    );

  if (assigned) {
    entries.push({
      label: "Assigned",
      value: assigned,
    });
  }

  const publicDate =
    formatDate(
      source.datePublic,
    );

  if (publicDate) {
    entries.push({
      label: "Public",
      value: publicDate,
    });
  }

  return entries;
}


const TEXT_SECTIONS: Array<{
  key: string;
  label: string;
}> = [
  {
    key: "descriptions",
    label: "Description",
  },
  {
    key: "workarounds",
    label: "Workarounds",
  },
  {
    key: "solutions",
    label: "Solutions",
  },
  {
    key: "exploits",
    label: "Exploits",
  },
  {
    key: "configurations",
    label: "Configurations",
  },
];


function textEntriesOf(
  source: AnyRecord,
  key: string,
): AnyRecord[] {
  return (
    source[key] as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


function supportingMediaOf(
  entry: AnyRecord,
): SupportingMediaItem[] {
  return (
    entry.supportingMedia as
      | SupportingMediaItem[]
      | undefined
  ) ?? [];
}


function affectedOf(
  source: AnyRecord,
): AnyRecord[] {
  return (
    source.affected as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


function affectedLabel(
  item: AnyRecord,
): string {
  if (
    item.vendor
    || item.product
  ) {
    return [
      item.vendor,
      item.product,
    ]
      .filter(Boolean)
      .join(" ");
  }

  if (item.packageName) {
    return String(
      item.packageName,
    );
  }

  if (item.collectionURL) {
    return String(
      item.collectionURL,
    );
  }

  return "Unnamed component";
}


function versionsOf(
  item: AnyRecord,
): AnyRecord[] {
  return (
    item.versions as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


function versionLabel(
  version: AnyRecord,
): string {
  const parts: string[] = [];

  if (version.version) {
    parts.push(
      String(
        version.version,
      ),
    );
  }

  if (version.lessThan) {
    parts.push(
      `< ${version.lessThan}`,
    );
  }

  if (version.lessThanOrEqual) {
    parts.push(
      `<= ${version.lessThanOrEqual}`,
    );
  }

  return (
    parts.join(" ")
    || "(unspecified version)"
  );
}


function problemTypesOf(
  source: AnyRecord,
): AnyRecord[] {
  return (
    source.problemTypes as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


function problemTypeDescriptionsOf(
  entry: AnyRecord,
): AnyRecord[] {
  return (
    entry.descriptions as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


function impactsOf(
  source: AnyRecord,
): AnyRecord[] {
  return (
    source.impacts as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


function impactDescriptionsOf(
  impact: AnyRecord,
): AnyRecord[] {
  return (
    impact.descriptions as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


function cpeApplicabilityOf(
  source: AnyRecord,
): AnyRecord[] {
  return (
    source.cpeApplicability as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


function nodesOf(
  statement: AnyRecord,
): AnyRecord[] {
  return (
    statement.nodes as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


function cpeMatchesOf(
  node: AnyRecord,
): AnyRecord[] {
  return (
    node.cpeMatch as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


const METRIC_FORMATS: Array<{
  key: string;
  label: string;
}> = [
  {
    key: "cvssV4_0",
    label: "CVSS 4.0",
  },
  {
    key: "cvssV3_1",
    label: "CVSS 3.1",
  },
  {
    key: "cvssV3_0",
    label: "CVSS 3.0",
  },
  {
    key: "cvssV2_0",
    label: "CVSS 2.0",
  },
];


interface DescribedMetric {
  label: string;
  vectorString?: string;
  baseScore?: number;
  baseSeverity?: string;
  otherContent?: string;
}


function metricsOf(
  source: AnyRecord,
): AnyRecord[] {
  return (
    source.metrics as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


function describeMetric(
  metric: AnyRecord,
): DescribedMetric {
  for (
    const format
    of METRIC_FORMATS
  ) {
    const value =
      metric[format.key] as
        | AnyRecord
        | undefined;

    if (value) {
      return {
        label:
          format.label,

        vectorString:
          value.vectorString as
            | string
            | undefined,

        baseScore:
          value.baseScore as
            | number
            | undefined,

        baseSeverity:
          value.baseSeverity as
            | string
            | undefined,
      };
    }
  }

  const other =
    metric.other as
      | AnyRecord
      | undefined;

  if (other) {
    return {
      label:
        (
          other.type as
            | string
            | undefined
        )
        ?? "Other",

      otherContent:
        typeof other.content ===
        "string"
          ? other.content
          : JSON.stringify(
              other.content,
            ),
    };
  }

  return {
    label:
      "Unrecognized format",
  };
}


function timelineOf(
  source: AnyRecord,
): AnyRecord[] {
  const entries =
    (
      source.timeline as
        | AnyRecord[]
        | undefined
    ) ?? [];

  return [...entries].sort(
    (a, b) => {
      return String(
        a.time,
      ).localeCompare(
        String(
          b.time,
        ),
      );
    },
  );
}


function referencesOf(
  source: AnyRecord,
): AnyRecord[] {
  return (
    source.references as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


function referenceUrl(
  reference: AnyRecord,
): string {
  return typeof reference.url ===
    "string"
    ? reference.url
    : "";
}


function referenceTagsOf(
  reference: AnyRecord,
): string[] {
  return (
    reference.tags as
      | string[]
      | undefined
  ) ?? [];
}


function creditsOf(
  source: AnyRecord,
): AnyRecord[] {
  return (
    source.credits as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


function taxonomyMappingsOf(
  source: AnyRecord,
): AnyRecord[] {
  return (
    source.taxonomyMappings as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


function taxonomyRelationsOf(
  mapping: AnyRecord,
): AnyRecord[] {
  return (
    mapping.taxonomyRelations as
      | AnyRecord[]
      | undefined
  ) ?? [];
}


function tagsOf(
  source: AnyRecord,
): string[] {
  return (
    source.tags as
      | string[]
      | undefined
  ) ?? [];
}


function sourceInfoOf(
  source: AnyRecord,
): AnyRecord | undefined {
  return source.source as
    | AnyRecord
    | undefined;
}


const CONTENT_KEYS = [
  ...TEXT_SECTIONS.map(
    (section) =>
      section.key,
  ),
  "affected",
  "problemTypes",
  "impacts",
  "cpeApplicability",
  "metrics",
  "timeline",
  "references",
  "credits",
  "taxonomyMappings",
  "tags",
];


function isEmptySource(
  source: AnyRecord,
): boolean {
  const hasArrayContent =
    CONTENT_KEYS.some(
      (key) => {
        const value =
          source[key];

        return (
          Array.isArray(value)
          && value.length > 0
        );
      },
    );

  return (
    !hasArrayContent
    && !sourceInfoOf(source)
  );
}
</script>


<template>
  <div class="card mb-4">
    <div class="card-header d-flex align-items-center gap-2">
      <span class="badge text-bg-secondary">
        {{ source.badge }}
      </span>

      <span class="fw-semibold">
        {{ source.label }}
      </span>
    </div>

    <div class="card-body">
      <p
        v-if="isEmptySource(source.data)"
        class="text-secondary mb-0"
      >
        No data provided by this source yet.
      </p>

      <template v-else>
        <div
          v-if="sourceDatesOf(source.data).length"
          class="small text-secondary mb-3"
        >
          <span
            v-for="entry in sourceDatesOf(source.data)"
            :key="entry.label"
            class="me-3"
          >
            {{ entry.label }}:
            {{ entry.value }}
          </span>
        </div>

        <template
          v-for="section in TEXT_SECTIONS"
          :key="section.key"
        >
          <div
            v-if="textEntriesOf(source.data, section.key).length"
            class="mb-4"
          >
            <h4 class="h6 text-uppercase text-secondary">
              {{ section.label }}
            </h4>

            <div
              v-for="(entry, index) in textEntriesOf(source.data, section.key)"
              :key="index"
              class="mb-2"
            >
              <span class="badge text-bg-light text-secondary border me-2">
                {{ entry.lang }}
              </span>

              {{ entry.value }}

              <SupportingMediaPreview
                v-for="(media, mediaIndex) in supportingMediaOf(entry)"
                :key="mediaIndex"
                :media="media"
              />
            </div>
          </div>
        </template>

        <div
          v-if="problemTypesOf(source.data).length"
          class="mb-4"
        >
          <h4 class="h6 text-uppercase text-secondary">
            Problem types
          </h4>

          <ul class="mb-0">
            <li
              v-for="(problemType, problemIndex) in problemTypesOf(source.data)"
              :key="problemIndex"
            >
              <span
                v-for="(description, descIndex) in problemTypeDescriptionsOf(problemType)"
                :key="descIndex"
              >
                {{
                  description.cweId
                    ? `${description.cweId} — `
                    : ""
                }}{{ description.description }}
              </span>
            </li>
          </ul>
        </div>

        <div
          v-if="affectedOf(source.data).length"
          class="mb-4"
        >
          <h4 class="h6 text-uppercase text-secondary">
            Affected products
          </h4>

          <div
            v-for="(item, index) in affectedOf(source.data)"
            :key="index"
            class="mb-3"
          >
            <div class="fw-semibold">
              {{ affectedLabel(item) }}
            </div>

            <div
              v-if="item.defaultStatus"
              class="small text-secondary"
            >
              Default status:
              {{ item.defaultStatus }}
            </div>

            <ul
              v-if="versionsOf(item).length"
              class="small mb-0"
            >
              <li
                v-for="(version, versionIndex) in versionsOf(item)"
                :key="versionIndex"
              >
                {{ versionLabel(version) }}
                —
                {{ version.status }}
              </li>
            </ul>
          </div>
        </div>

        <div
          v-if="cpeApplicabilityOf(source.data).length"
          class="mb-4"
        >
          <h4 class="h6 text-uppercase text-secondary">
            CPE applicability
          </h4>

          <div
            v-for="(statement, sIndex) in cpeApplicabilityOf(source.data)"
            :key="sIndex"
            class="mb-2"
          >
            <div
              v-for="(node, nIndex) in nodesOf(statement)"
              :key="nIndex"
              class="ms-2 mb-1"
            >
              <span class="text-secondary small">
                {{
                  node.operator
                    ?? "AND"
                }}{{
                  node.negate
                    ? " (negated)"
                    : ""
                }}
              </span>

              <ul class="small mb-0">
                <li
                  v-for="(match, mIndex) in cpeMatchesOf(node)"
                  :key="mIndex"
                >
                  <code>
                    {{ match.criteria }}
                  </code>

                  <span class="text-secondary">
                    —
                    {{
                      match.vulnerable === false
                        ? "not vulnerable"
                        : "vulnerable"
                    }}
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div
          v-if="impactsOf(source.data).length"
          class="mb-4"
        >
          <h4 class="h6 text-uppercase text-secondary">
            Impacts
          </h4>

          <ul class="mb-0">
            <li
              v-for="(impact, index) in impactsOf(source.data)"
              :key="index"
            >
              <span
                v-if="impact.capecId"
                class="text-secondary"
              >
                {{ impact.capecId }}
                —
              </span>

              <div
                v-for="(description, descIndex) in impactDescriptionsOf(impact)"
                :key="descIndex"
              >
                {{ description.value }}

                <SupportingMediaPreview
                  v-for="(media, mediaIndex) in supportingMediaOf(description)"
                  :key="mediaIndex"
                  :media="media"
                />
              </div>
            </li>
          </ul>
        </div>

        <div
          v-if="metricsOf(source.data).length"
          class="mb-4"
        >
          <h4 class="h6 text-uppercase text-secondary">
            Metrics
          </h4>

          <div
            v-for="(metric, index) in metricsOf(source.data)"
            :key="index"
            class="mb-2"
          >
            <template
              v-if="describeMetric(metric).otherContent === undefined"
            >
              <span class="badge text-bg-secondary me-2">
                {{ describeMetric(metric).label }}
              </span>

              <span
                v-if="describeMetric(metric).baseSeverity"
                class="me-2"
              >
                {{ describeMetric(metric).baseScore }}
                ({{ describeMetric(metric).baseSeverity }})
              </span>

              <code class="small">
                {{ describeMetric(metric).vectorString }}
              </code>
            </template>

            <template v-else>
              <span class="badge text-bg-secondary me-2">
                {{ describeMetric(metric).label }}
              </span>

              <span class="small">
                {{ describeMetric(metric).otherContent }}
              </span>
            </template>
          </div>
        </div>

        <div
          v-if="timelineOf(source.data).length"
          class="mb-4"
        >
          <h4 class="h6 text-uppercase text-secondary">
            Timeline
          </h4>

          <ul class="mb-0">
            <li
              v-for="(event, index) in timelineOf(source.data)"
              :key="index"
            >
              <span class="text-secondary small">
                {{
                  formatDate(event.time)
                    ?? event.time
                }}
              </span>

              —
              {{ event.value }}
            </li>
          </ul>
        </div>

        <div
          v-if="creditsOf(source.data).length"
          class="mb-4"
        >
          <h4 class="h6 text-uppercase text-secondary">
            Credits
          </h4>

          <ul class="mb-0">
            <li
              v-for="(credit, index) in creditsOf(source.data)"
              :key="index"
            >
              {{ credit.value }}

              <span
                v-if="credit.type"
                class="text-secondary small"
              >
                ({{ credit.type }})
              </span>
            </li>
          </ul>
        </div>

        <div
          v-if="referencesOf(source.data).length"
          class="mb-4"
        >
          <h4 class="h6 text-uppercase text-secondary">
            References
          </h4>

          <ul class="mb-0">
            <li
              v-for="(reference, index) in referencesOf(source.data)"
              :key="index"
            >
              <a
                :href="referenceUrl(reference)"
                target="_blank"
                rel="noopener noreferrer"
              >
                {{
                  reference.name
                    || reference.url
                }}
              </a>

              <span
                v-for="(tag, tagIndex) in referenceTagsOf(reference)"
                :key="tagIndex"
                class="badge text-bg-light text-secondary border ms-1"
              >
                {{ tag }}
              </span>
            </li>
          </ul>
        </div>

        <div
          v-if="taxonomyMappingsOf(source.data).length"
          class="mb-4"
        >
          <h4 class="h6 text-uppercase text-secondary">
            Taxonomy mappings
          </h4>

          <div
            v-for="(mapping, index) in taxonomyMappingsOf(source.data)"
            :key="index"
            class="mb-2"
          >
            <div class="fw-semibold">
              {{ mapping.taxonomyName }}

              <span
                v-if="mapping.taxonomyVersion"
                class="text-secondary fw-normal"
              >
                v{{ mapping.taxonomyVersion }}
              </span>
            </div>

            <ul class="small mb-0">
              <li
                v-for="(relation, relationIndex) in taxonomyRelationsOf(mapping)"
                :key="relationIndex"
              >
                {{ relation.taxonomyId }}
                —
                {{ relation.relationshipName }}
                —
                {{ relation.relationshipValue }}
              </li>
            </ul>
          </div>
        </div>

        <div
          v-if="tagsOf(source.data).length"
          class="mb-4"
        >
          <h4 class="h6 text-uppercase text-secondary">
            Tags
          </h4>

          <span
            v-for="(tag, index) in tagsOf(source.data)"
            :key="index"
            class="badge text-bg-light text-secondary border me-1"
          >
            {{ tag }}
          </span>
        </div>

        <div
          v-if="sourceInfoOf(source.data)"
        >
          <h4 class="h6 text-uppercase text-secondary">
            Source
          </h4>

          <dl class="row mb-0 small">
            <template
              v-for="(value, key) in sourceInfoOf(source.data)"
              :key="key"
            >
              <dt class="col-sm-3 text-secondary">
                {{ key }}
              </dt>

              <dd
                v-if="isComplexValue(value)"
                class="col-sm-9"
              >
                <details>
                  <summary class="text-secondary">
                    Show details
                  </summary>

                  <pre class="preview-json-value mb-0 mt-1">{{ formatValueJson(value) }}</pre>
                </details>
              </dd>

              <dd
                v-else
                class="col-sm-9"
              >
                {{ formatValue(value) }}
              </dd>
            </template>
          </dl>
        </div>
      </template>
    </div>
  </div>
</template>


<style scoped>
.preview-json-value {
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 20rem;
  overflow-y: auto;
}
</style>
