<script setup lang="ts">
import {
  computed,
} from "vue";

import {
  useEditorContext,
} from "../../../core/context";

import {
  definedGroups,
  definedProducts,
} from "../../../renderers/csaf/products";

import {
  formatDate,
  safeUrl,
} from "../common/utils";

import {
  PRODUCT_STATUSES,
  label,
  list,
  obj,
  scores,
  strings,
  text,
} from "./csaf-preview";

/*
 * A read-only rendering of a CSAF 2.1 advisory: document metadata and
 * notes, the products, each vulnerability with its product status,
 * scores and remediations, and the revision history. Product and
 * group IDs are shown with their names from the product tree.
 */
const editor = useEditorContext();

const record = computed(() => obj(editor.record.value));
const meta = computed(() => obj(record.value.document));
const tracking = computed(() => obj(meta.value.tracking));
const publisher = computed(() => obj(meta.value.publisher));
const distribution = computed(() => obj(meta.value.distribution));

const products = computed(() => definedProducts(record.value));
const groups = computed(() => definedGroups(record.value));

const productNames = computed(() => new Map(products.value.map((product) => [product.id, product.name])));
const groupNames = computed(() => new Map(groups.value.map((group) => [group.id, group.name])));

const vulnerabilities = computed(() => list(record.value.vulnerabilities));
const revisions = computed(() => list(tracking.value.revision_history));

const documentFacts = computed(() => {
  const tlp = obj(distribution.value.tlp);
  const sharingGroup = obj(distribution.value.sharing_group);

  return [
    ["Publisher", [text(publisher.value.name), text(publisher.value.category) && `(${label(text(publisher.value.category))})`].filter(Boolean).join(" ")],
    ["Namespace", text(publisher.value.namespace)],
    ["Category", text(meta.value.category)],
    ["Distribution", [text(tlp.label) && `TLP:${text(tlp.label)}`, text(sharingGroup.name)].filter(Boolean).join(" · ")],
    ["Aggregate severity", text(obj(meta.value.aggregate_severity).text)],
    ["Language", text(meta.value.lang)],
    ["Initial release", formatDate(tracking.value.initial_release_date) ?? ""],
    ["Current release", formatDate(tracking.value.current_release_date) ?? ""],
  ].filter(([, value]) => value) as [string, string][];
});

function productStatus(
  vulnerability: Record<string, unknown>,
): { status: string; ids: string[] }[] {
  const status = obj(vulnerability.product_status);

  return PRODUCT_STATUSES
    .map((key) => ({ status: label(key), ids: strings(status[key]) }))
    .filter((entry) => entry.ids.length);
}

function vulnerabilityDates(
  vulnerability: Record<string, unknown>,
): [string, string][] {
  return ([
    ["Disclosure", vulnerability.disclosure_date],
    ["Discovery", vulnerability.discovery_date],
  ] as const).flatMap(([name, value]) => {
    const formatted = formatDate(value);

    return formatted ? [[name, formatted] as [string, string]] : [];
  });
}
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

    <div class="card mb-4">
      <div class="card-body">
        <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
          <h3 class="h5 mb-0">
            {{ text(tracking.id) || "Unassigned tracking ID" }}
          </h3>

          <span class="badge text-bg-light text-secondary border">
            CSAF {{ text(meta.csaf_version) || "2.1" }}
          </span>

          <span
            v-if="text(tracking.status)"
            class="badge"
            :class="text(tracking.status) === 'draft' ? 'text-bg-warning' : 'text-bg-secondary'"
          >
            {{ text(tracking.status) }} {{ text(tracking.version) }}
          </span>
        </div>

        <p
          v-if="text(meta.title)"
          class="fw-semibold mb-2"
        >
          {{ text(meta.title) }}
        </p>

        <dl class="row mb-0 small">
          <template
            v-for="[name, value] in documentFacts"
            :key="name"
          >
            <dt class="col-sm-3 text-secondary">
              {{ name }}
            </dt>

            <dd class="col-sm-9">
              {{ value }}
            </dd>
          </template>
        </dl>
      </div>
    </div>

    <div
      v-if="list(meta.notes).length"
      class="card mb-4"
    >
      <div class="card-body">
        <h3 class="h6 text-secondary text-uppercase">
          Notes
        </h3>

        <div
          v-for="(note, index) in list(meta.notes)"
          :key="index"
          class="mb-3"
        >
          <div class="d-flex align-items-center gap-2">
            <span class="badge text-bg-light border">{{ label(text(note.category)) }}</span>
            <strong v-if="text(note.title)">{{ text(note.title) }}</strong>
          </div>

          <p
            class="mb-0 mt-1"
            style="white-space: pre-wrap"
          >
            {{ text(note.text) }}
          </p>
        </div>
      </div>
    </div>

    <div
      v-if="products.length"
      class="card mb-4"
    >
      <div class="card-body">
        <h3 class="h6 text-secondary text-uppercase">
          Products
        </h3>

        <table class="table table-sm small mb-0">
          <tbody>
            <tr
              v-for="product in products"
              :key="product.id"
            >
              <!-- As narrow as the IDs, so the names line up beside them. -->
              <td
                class="text-nowrap pe-3"
                style="width: 1%"
              >
                <code>{{ product.id }}</code>
              </td>
              <td>{{ product.name }}</td>
            </tr>
          </tbody>
        </table>

        <template v-if="groups.length">
          <h4 class="h6 text-secondary mt-3">
            Product groups
          </h4>

          <ul class="small mb-0">
            <li
              v-for="group in groups"
              :key="group.id"
            >
              <code>{{ group.id }}</code> {{ group.name }}
            </li>
          </ul>
        </template>
      </div>
    </div>

    <div
      v-for="(vulnerability, index) in vulnerabilities"
      :key="index"
      class="card mb-4"
    >
      <div class="card-body">
        <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
          <h3 class="h5 mb-0">
            {{ text(vulnerability.cve) || text(vulnerability.title) || `Vulnerability ${index + 1}` }}
          </h3>

          <span
            v-for="id in list(vulnerability.ids)"
            :key="text(id.text)"
            class="badge text-bg-light border"
          >
            {{ text(id.system_name) }}: {{ text(id.text) }}
          </span>

          <span
            v-for="cwe in list(vulnerability.cwes)"
            :key="text(cwe.id)"
            class="badge text-bg-light border"
            :title="text(cwe.name)"
          >
            {{ text(cwe.id) }}
          </span>
        </div>

        <p
          v-if="text(vulnerability.cve) && text(vulnerability.title)"
          class="fw-semibold mb-2"
        >
          {{ text(vulnerability.title) }}
        </p>

        <dl
          v-if="vulnerabilityDates(vulnerability).length"
          class="row small mb-2"
        >
          <template
            v-for="[name, value] in vulnerabilityDates(vulnerability)"
            :key="name"
          >
            <dt class="col-sm-3 text-secondary">
              {{ name }}
            </dt>
            <dd class="col-sm-9">
              {{ value }}
            </dd>
          </template>
        </dl>

        <div
          v-for="(note, noteIndex) in list(vulnerability.notes)"
          :key="`n${noteIndex}`"
          class="mb-2"
        >
          <strong
            v-if="text(note.title)"
            class="small"
          >{{ text(note.title) }}</strong>
          <p
            class="mb-0"
            style="white-space: pre-wrap"
          >
            {{ text(note.text) }}
          </p>
        </div>

        <template v-if="productStatus(vulnerability).length">
          <h4 class="h6 text-secondary text-uppercase mt-3">
            Product status
          </h4>

          <dl class="row small mb-0">
            <template
              v-for="entry in productStatus(vulnerability)"
              :key="entry.status"
            >
              <dt class="col-sm-3 text-secondary">
                {{ entry.status }}
              </dt>

              <dd class="col-sm-9">
                <span
                  v-for="id in entry.ids"
                  :key="id"
                  class="d-block"
                >
                  <code>{{ id }}</code>
                  <span
                    v-if="productNames.get(id)"
                    class="ms-1"
                  >{{ productNames.get(id) }}</span>
                  <span
                    v-else
                    class="ms-1 text-warning-emphasis"
                  >not defined in the product tree</span>
                </span>
              </dd>
            </template>
          </dl>
        </template>

        <template v-if="list(vulnerability.metrics).length">
          <h4 class="h6 text-secondary text-uppercase mt-3">
            Scores
          </h4>

          <div
            v-for="(metric, metricIndex) in list(vulnerability.metrics)"
            :key="`m${metricIndex}`"
            class="small mb-2"
          >
            <div
              v-for="score in scores(obj(metric.content))"
              :key="score.kind"
            >
              <strong>{{ score.kind }}</strong>
              <span class="ms-2">{{ score.value }}</span>
              <code
                v-if="score.detail"
                class="ms-2"
              >{{ score.detail }}</code>
            </div>

            <div class="text-secondary">
              for {{ strings(metric.products).map((id) => productNames.get(id) || id).join(", ") || "no products" }}
              <template v-if="text(metric.source)">
                · source
                <a
                  :href="safeUrl(metric.source)"
                  target="_blank"
                  rel="noopener noreferrer"
                >{{ text(metric.source) }}</a>
              </template>
            </div>
          </div>
        </template>

        <template v-if="list(vulnerability.remediations).length">
          <h4 class="h6 text-secondary text-uppercase mt-3">
            Remediations
          </h4>

          <div
            v-for="(remediation, remediationIndex) in list(vulnerability.remediations)"
            :key="`r${remediationIndex}`"
            class="small mb-2"
          >
            <span class="badge text-bg-light border me-1">{{ label(text(remediation.category)) }}</span>
            {{ text(remediation.details) }}
            <a
              v-if="safeUrl(remediation.url)"
              :href="safeUrl(remediation.url)"
              target="_blank"
              rel="noopener noreferrer"
              class="ms-1"
            >{{ text(remediation.url) }}</a>

            <div class="text-secondary">
              for {{ [
                ...strings(remediation.product_ids).map((id) => productNames.get(id) || id),
                ...strings(remediation.group_ids).map((id) => groupNames.get(id) || id),
              ].join(", ") || "no products" }}
            </div>
          </div>
        </template>

        <template v-if="list(vulnerability.threats).length || list(vulnerability.flags).length">
          <h4 class="h6 text-secondary text-uppercase mt-3">
            Threats and flags
          </h4>

          <ul class="small mb-0">
            <li
              v-for="(threat, threatIndex) in list(vulnerability.threats)"
              :key="`t${threatIndex}`"
            >
              <span class="text-secondary">{{ label(text(threat.category)) }}:</span>
              {{ text(threat.details) }}
            </li>

            <li
              v-for="(flag, flagIndex) in list(vulnerability.flags)"
              :key="`f${flagIndex}`"
            >
              <span class="text-secondary">Flag:</span>
              {{ label(text(flag.label)) }}
              <span class="text-secondary">
                · {{ strings(flag.product_ids).map((id) => productNames.get(id) || id).join(", ") }}
              </span>
            </li>
          </ul>
        </template>

        <template v-if="list(vulnerability.references).length">
          <h4 class="h6 text-secondary text-uppercase mt-3">
            References
          </h4>

          <ul class="small mb-0">
            <li
              v-for="(reference, referenceIndex) in list(vulnerability.references)"
              :key="`ref${referenceIndex}`"
            >
              <a
                :href="safeUrl(reference.url)"
                target="_blank"
                rel="noopener noreferrer"
              >{{ text(reference.summary) || text(reference.url) }}</a>
            </li>
          </ul>
        </template>

        <template v-if="list(vulnerability.acknowledgments).length">
          <h4 class="h6 text-secondary text-uppercase mt-3">
            Acknowledgments
          </h4>

          <ul class="small mb-0">
            <li
              v-for="(ack, ackIndex) in list(vulnerability.acknowledgments)"
              :key="`a${ackIndex}`"
            >
              {{ [...strings(ack.names), text(ack.organization)].filter(Boolean).join(", ") }}
              <span
                v-if="text(ack.summary)"
                class="text-secondary"
              >· {{ text(ack.summary) }}</span>
            </li>
          </ul>
        </template>
      </div>
    </div>

    <div
      v-if="list(meta.references).length || list(meta.acknowledgments).length"
      class="card mb-4"
    >
      <div class="card-body">
        <template v-if="list(meta.references).length">
          <h3 class="h6 text-secondary text-uppercase">
            References
          </h3>

          <ul class="small">
            <li
              v-for="(reference, index) in list(meta.references)"
              :key="index"
            >
              <span
                v-if="text(reference.category)"
                class="badge text-bg-light border me-1"
              >{{ text(reference.category) }}</span>
              <a
                :href="safeUrl(reference.url)"
                target="_blank"
                rel="noopener noreferrer"
              >{{ text(reference.summary) || text(reference.url) }}</a>
            </li>
          </ul>
        </template>

        <template v-if="list(meta.acknowledgments).length">
          <h3 class="h6 text-secondary text-uppercase">
            Acknowledgments
          </h3>

          <ul class="small mb-0">
            <li
              v-for="(ack, index) in list(meta.acknowledgments)"
              :key="index"
            >
              {{ [...strings(ack.names), text(ack.organization)].filter(Boolean).join(", ") }}
              <span
                v-if="text(ack.summary)"
                class="text-secondary"
              >· {{ text(ack.summary) }}</span>
            </li>
          </ul>
        </template>
      </div>
    </div>

    <div
      v-if="revisions.length"
      class="card mb-4"
    >
      <div class="card-body">
        <h3 class="h6 text-secondary text-uppercase">
          Revision history
        </h3>

        <table class="table table-sm small mb-0">
          <thead>
            <tr>
              <th scope="col">
                Version
              </th>
              <th scope="col">
                Date
              </th>
              <th scope="col">
                Summary
              </th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="(revision, index) in revisions"
              :key="index"
            >
              <td><code>{{ text(revision.number) }}</code></td>
              <td class="text-nowrap">
                {{ formatDate(revision.date) }}
              </td>
              <td>{{ text(revision.summary) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
