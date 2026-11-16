<script setup lang="ts">
import {
  computed,
  ref,
} from "vue";

import type {
  EditorContext,
  PublicRecord,
} from "../../contracts";

import {
  useEditorContext,
  useEditorRepository,
} from "../../core/context";

import {
  safeUrl,
} from "../../sections/preview/common/utils";

import {
  differences,
  vulnerabilityIds,
} from "./compare";

import type {
  Difference,
} from "./compare";

const props = defineProps<{
  context: EditorContext;
}>();

/*
 * Compares each vulnerability of a CSAF advisory with the public GCVE/CVE
 * records it cites (looked up by the backend's GCVE client), and can take
 * public values over.
 */
const repository = useEditorRepository();
const editor = useEditorContext();

type JsonObject = Record<string, unknown>;

interface Lookup {
  id: string;
  result?: PublicRecord;
  error?: string;
}

const supported = computed(() => Boolean(repository.value?.lookupPublicRecord));
const loading = ref(false);
// Per vulnerability index, one lookup per cited ID.
const lookups = ref<Record<number, Lookup[]>>({});

const vulnerabilities = computed(() => {
  const value = props.context.record.vulnerabilities;

  return Array.isArray(value) ? value as JsonObject[] : [];
});

const cited = computed(() => vulnerabilities.value.map((vulnerability) => vulnerabilityIds(vulnerability)));

async function compare(): Promise<void> {
  const lookup = repository.value?.lookupPublicRecord;

  if (!lookup) {
    return;
  }

  loading.value = true;
  lookups.value = {};

  await Promise.all(cited.value.map(async (ids, index) => {
    lookups.value[index] = await Promise.all(ids.map(async (id): Promise<Lookup> => {
      try {
        return { id, result: await lookup.call(repository.value, id) };
      } catch (error) {
        return { id, error: error instanceof Error ? error.message : String(error) };
      }
    }));
  }));

  loading.value = false;
}

function found(index: number, lookup: Lookup): Difference[] {
  const vulnerability = vulnerabilities.value[index];

  return vulnerability && lookup.result ? differences(vulnerability, lookup.result.csaf) : [];
}

function isRejected(lookup: Lookup): boolean {
  return lookup.result?.record.cveMetadata?.state === "REJECTED";
}

function apply(index: number, difference: Difference): void {
  const vulnerability = vulnerabilities.value[index];

  if (!vulnerability || !difference.apply) {
    return;
  }

  difference.apply(vulnerability);
  editor.notice.value = `Took the public ${difference.label.toLowerCase()} over. Save to keep the changes.`;
}
</script>

<template>
  <section>
    <header class="mb-3">
      <h2 class="h4">
        Compare vulnerabilities
      </h2>

      <p class="text-secondary">
        Compares each vulnerability with the public GCVE or CVE record it cites,
        as published by its GNA or, for CVE IDs, as aggregated by Vulnerability-Lookup.
      </p>
    </header>

    <p
      v-if="!supported"
      class="text-secondary"
    >
      Looking up public records isn't available here.
    </p>

    <template v-else>
      <p
        v-if="!cited.some((ids) => ids.length)"
        class="text-secondary"
      >
        No vulnerability cites a CVE or GCVE ID yet (<code>cve</code>, or an
        ID with system name GCVE).
      </p>

      <button
        v-else
        type="button"
        class="btn btn-primary btn-sm mb-3"
        :disabled="loading"
        @click="compare"
      >
        {{ loading ? "Looking up…" : "Compare with public records" }}
      </button>

      <div
        v-for="(ids, index) in cited"
        :key="index"
        class="card mb-3"
      >
        <div class="card-body">
          <h3 class="h6">
            {{ (vulnerabilities[index]?.title as string) || `Vulnerability ${index + 1}` }}
            <span class="text-secondary fw-normal">· {{ ids.join(", ") || "no CVE or GCVE ID" }}</span>
          </h3>

          <div
            v-for="lookup in lookups[index] ?? []"
            :key="lookup.id"
            class="border-top pt-2 mt-2"
          >
            <div class="d-flex flex-wrap align-items-center gap-2 small">
              <strong>{{ lookup.id }}</strong>

              <template v-if="lookup.result">
                <a
                  :href="safeUrl(lookup.result.url)"
                  target="_blank"
                  rel="noopener noreferrer"
                >{{ lookup.result.source }}</a>

                <span
                  v-if="isRejected(lookup)"
                  class="badge text-bg-danger"
                >REJECTED</span>
              </template>

              <span
                v-else
                class="text-danger"
              >{{ lookup.error }}</span>
            </div>

            <p
              v-if="isRejected(lookup)"
              class="small text-danger mt-1 mb-0"
            >
              The public record is rejected: this advisory may cite a withdrawn ID.
            </p>

            <p
              v-if="lookup.result && !found(index, lookup).length"
              class="small text-success mt-1 mb-0"
            >
              Matches the public record.
            </p>

            <table
              v-else-if="lookup.result"
              class="table table-sm small mt-2 mb-0"
            >
              <thead>
                <tr>
                  <th scope="col">
                    Field
                  </th>
                  <th scope="col">
                    This advisory
                  </th>
                  <th scope="col">
                    Public record
                  </th>
                  <th scope="col" />
                </tr>
              </thead>

              <tbody>
                <tr
                  v-for="difference in found(index, lookup)"
                  :key="difference.field"
                >
                  <td class="text-nowrap">
                    {{ difference.label }}
                  </td>
                  <td style="white-space: pre-wrap">
                    {{ difference.ours || "–" }}
                  </td>
                  <td style="white-space: pre-wrap">
                    {{ difference.theirs }}
                  </td>
                  <td class="text-end">
                    <button
                      v-if="difference.apply"
                      type="button"
                      class="btn btn-outline-primary btn-sm text-nowrap"
                      @click="apply(index, difference)"
                    >
                      Use public
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>
