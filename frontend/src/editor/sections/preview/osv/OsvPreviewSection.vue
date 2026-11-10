<script setup lang="ts">
import {
  computed,
} from "vue";

import {
  useEditorContext,
} from "../../../core/context";

import {
  formatDate,
  safeUrl,
} from "../common/utils";

import {
  findXGcveOccurrences,
} from "../../../gcve";

import MetadataPreview from
  "../cve/MetadataPreview.vue";

import GcvePreview from
  "../gcve/GcvePreview.vue";

import SchemaValuePreview from
  "../common/SchemaValuePreview.vue";

import type {
  PreviewDate,
} from "../cve/types";


type AnyRecord = Record<string, unknown>;


const editor =
  useEditorContext();

const record =
  computed<AnyRecord>(() => {
    return (
      editor.record.value ?? {}
    ) as AnyRecord;
  });


function list(
  value: unknown,
): AnyRecord[] {
  return Array.isArray(value)
    ? value.filter(
        (item): item is AnyRecord =>
          typeof item === "object" && item !== null,
      )
    : [];
}

function strings(
  value: unknown,
): string[] {
  return Array.isArray(value)
    ? value.filter(
        (item): item is string =>
          typeof item === "string" && item !== "",
      )
    : [];
}

function text(
  value: unknown,
): string {
  return typeof value === "string" ? value : "";
}


const dates =
  computed<PreviewDate[]>(() => {
    return ([
      ["published", "Published"],
      ["modified", "Modified"],
      ["withdrawn", "Withdrawn"],
    ] as const).flatMap(([key, label]) => {
      const value =
        formatDate(record.value[key]);

      return value ? [{ label, value }] : [];
    });
  });

const aliases =
  computed(() => strings(record.value.aliases));

const related =
  computed(() => strings(record.value.related));

const upstream =
  computed(() => strings(record.value.upstream));

const severity =
  computed(() => list(record.value.severity));

const references =
  computed(() => list(record.value.references));

const credits =
  computed(() => list(record.value.credits));

// GCVE-BCP-05 data patch2vuln puts in database_specific.x_gcve.
const gcveOccurrences =
  computed(() => findXGcveOccurrences(record.value));

// The rest of database_specific (e.g. patch2vuln's cwe_ids, capec_ids,
// ssvc); x_gcve has its own card below.
const databaseSpecific =
  computed(() => {
    const value = record.value.database_specific;

    return typeof value === "object" && value !== null && !Array.isArray(value)
      ? Object.entries(value).filter(([key, entry]) => key !== "x_gcve" && entry !== undefined)
      : [];
  });

function keyLabel(
  key: string,
): string {
  const words = key.replace(/_/g, " ");

  return words.charAt(0).toUpperCase() + words.slice(1);
}


const affected =
  computed(() => {
    return list(record.value.affected).map((entry) => {
      const pkg =
        (entry.package ?? {}) as AnyRecord;

      return {
        ecosystem: text(pkg.ecosystem),
        name: text(pkg.name),
        purl: text(pkg.purl),
        versions: strings(entry.versions),
        severity: list(entry.severity),
        ranges: list(entry.ranges).map((range) => ({
          type: text(range.type),
          repo: text(range.repo),
          // Each OSV event object holds exactly one of these keys.
          events: list(range.events).flatMap((event) =>
            Object.entries(event).map(
              ([kind, value]) => `${kind.replace("_", " ")} ${String(value)}`,
            ),
          ),
        })),
      };
    });
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
        text(record.id) || 'Unassigned identifier'
      "
      :secondary-identifier="
        text(record.schema_version)
          ? `OSV ${text(record.schema_version)}`
          : undefined
      "
      :state="record.withdrawn ? 'Withdrawn' : undefined"
      :dates="dates"
    />

    <div
      v-if="text(record.summary) || text(record.details)"
      class="card mb-4"
    >
      <div class="card-body">
        <h3
          v-if="text(record.summary)"
          class="h5"
        >
          {{ text(record.summary) }}
        </h3>

        <p
          v-if="text(record.details)"
          class="mb-0"
          style="white-space: pre-wrap"
        >
          {{ text(record.details) }}
        </p>
      </div>
    </div>

    <div
      v-if="
        aliases.length
          || related.length
          || upstream.length
          || severity.length
      "
      class="card mb-4"
    >
      <div class="card-body">
        <dl class="row mb-0 small">
          <template
            v-for="[label, values] in ([
              ['Aliases', aliases],
              ['Related', related],
              ['Upstream', upstream],
            ] as const)"
            :key="label"
          >
            <template v-if="values.length">
              <dt class="col-sm-3 text-secondary">
                {{ label }}
              </dt>

              <dd class="col-sm-9">
                <span
                  v-for="value in values"
                  :key="value"
                  class="badge text-bg-light border me-1"
                >
                  {{ value }}
                </span>
              </dd>
            </template>
          </template>

          <template v-if="severity.length">
            <dt class="col-sm-3 text-secondary">
              Severity
            </dt>

            <dd class="col-sm-9">
              <div
                v-for="(entry, index) in severity"
                :key="index"
              >
                <strong>{{ text(entry.type) }}</strong>
                <code class="ms-2">{{ text(entry.score) }}</code>
              </div>
            </dd>
          </template>
        </dl>
      </div>
    </div>

    <div
      v-if="affected.length"
      class="card mb-4"
    >
      <div class="card-body">
        <h3 class="h6 text-secondary text-uppercase">
          Affected packages
        </h3>

        <div
          v-for="(entry, index) in affected"
          :key="index"
          class="border-top pt-2 mt-2"
        >
          <div class="d-flex flex-wrap align-items-center gap-2">
            <span
              v-if="entry.ecosystem"
              class="badge text-bg-secondary"
            >
              {{ entry.ecosystem }}
            </span>

            <strong>{{ entry.name || "Unnamed package" }}</strong>

            <code
              v-if="entry.purl"
              class="small"
            >
              {{ entry.purl }}
            </code>
          </div>

          <ul class="small mb-1 mt-1">
            <li
              v-for="(range, rangeIndex) in entry.ranges"
              :key="rangeIndex"
            >
              <span class="text-secondary">{{ range.type }}</span>
              <span v-if="range.repo"> ({{ range.repo }})</span>:
              {{ range.events.join(", ") || "no events" }}
            </li>

            <li v-if="entry.versions.length">
              <span class="text-secondary">Versions</span>:
              {{ entry.versions.join(", ") }}
            </li>

            <li
              v-for="(entrySeverity, severityIndex) in entry.severity"
              :key="`s${severityIndex}`"
            >
              <span class="text-secondary">{{ text(entrySeverity.type) }}</span>:
              <code>{{ text(entrySeverity.score) }}</code>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <div
      v-if="references.length"
      class="card mb-4"
    >
      <div class="card-body">
        <h3 class="h6 text-secondary text-uppercase">
          References
        </h3>

        <ul class="small mb-0">
          <li
            v-for="(reference, index) in references"
            :key="index"
          >
            <span
              v-if="text(reference.type)"
              class="badge text-bg-light border me-1"
            >
              {{ text(reference.type) }}
            </span>

            <a
              :href="safeUrl(reference.url)"
              target="_blank"
              rel="noopener noreferrer"
            >
              {{ text(reference.url) }}
            </a>
          </li>
        </ul>
      </div>
    </div>

    <div
      v-if="credits.length"
      class="card mb-4"
    >
      <div class="card-body">
        <h3 class="h6 text-secondary text-uppercase">
          Credits
        </h3>

        <ul class="small mb-0">
          <li
            v-for="(credit, index) in credits"
            :key="index"
          >
            {{ text(credit.name) }}
            <span
              v-if="text(credit.type)"
              class="text-secondary"
            >
              ({{ text(credit.type).toLowerCase().replace(/_/g, " ") }})
            </span>
          </li>
        </ul>
      </div>
    </div>

    <div
      v-if="databaseSpecific.length"
      class="card mb-4"
    >
      <div class="card-body">
        <h3 class="h6 text-secondary text-uppercase">
          Database specific
        </h3>

        <dl class="row mb-0 small">
          <template
            v-for="[key, value] in databaseSpecific"
            :key="key"
          >
            <dt class="col-sm-3 text-secondary">
              {{ keyLabel(key) }}
            </dt>

            <dd class="col-sm-9">
              <SchemaValuePreview :value="value" />
            </dd>
          </template>
        </dl>
      </div>
    </div>

    <GcvePreview
      v-if="gcveOccurrences.length"
      :occurrences="gcveOccurrences"
    />
  </section>
</template>
