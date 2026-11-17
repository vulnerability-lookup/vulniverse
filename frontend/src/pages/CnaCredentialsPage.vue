<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import { apiRequest } from "@/repositories/apiRequest";
import { ApiError } from "@/shared/errors";
import { HttpRepository } from "@/repositories/HttpRepository";
import type { PublicationTarget } from "@/editor/contracts";

interface TargetInfo {
  id: PublicationTarget;
  label: string;
}

const TARGETS: TargetInfo[] = [
  { id: "vl", label: "Vulnerability-Lookup" },
  { id: "cve-program", label: "CVE Program" },
];

/** A server the operator allows publishing to ([[panels.<target>.instances]]). */
interface Instance {
  id: string;
  name: string;
  url: string;
}

interface StoredCredential {
  /** "" when an older stored URL matched none of the instances. */
  instance: string;
  shortName: string;
  orgId: string;
  cveApiOrg: string;
  cveApiUser: string;
}

interface FormState {
  instance: string;
  shortName: string;
  orgId: string;
  cveApiOrg: string;
  cveApiUser: string;
  cveApiKey: string;
}

function emptyForm(): FormState {
  return {
    instance: "",
    shortName: "",
    orgId: "",
    cveApiOrg: "",
    cveApiUser: "",
    cveApiKey: "",
  };
}

const configured = reactive<Partial<Record<PublicationTarget, StoredCredential>>>({});
const forms = reactive<Record<PublicationTarget, FormState>>({
  vl: emptyForm(),
  "cve-program": emptyForm(),
});
const savingTarget = ref<PublicationTarget | null>(null);
const errors = reactive<Partial<Record<PublicationTarget, string>>>({});
const loading = ref(true);

const repository = new HttpRepository("/api/v1");
const panelFlags = ref<Record<string, boolean>>({});
const instances = ref<Partial<Record<PublicationTarget, Instance[]>>>({});

function instancesOf(target: PublicationTarget): Instance[] {
  return instances.value[target] ?? [];
}

function urlOf(target: PublicationTarget): string | undefined {
  return instancesOf(target).find((instance) => instance.id === forms[target].instance)?.url;
}

// The stored key only goes to the instance it was entered for.
function needsKey(target: PublicationTarget): boolean {
  return configured[target]?.instance !== forms[target].instance;
}

// A panel id absent from config defaults to enabled — same convention
// as editor/enabled-extensions.ts's filterEnabled() and AppHeader.vue's
// showCnaCredentialsLink.
const visibleTargets = computed(() =>
  TARGETS.filter((target) => panelFlags.value[target.id] ?? true),
);

async function load(): Promise<void> {
  loading.value = true;

  const [result, capabilities, available] = await Promise.all([
    apiRequest<Record<string, StoredCredential>>("/cna-credentials"),
    repository.getCapabilities(),
    apiRequest<Record<PublicationTarget, Instance[]>>("/cna-credentials/instances"),
  ]);

  panelFlags.value = capabilities.panels;
  instances.value = available;

  for (const target of TARGETS) {
    const stored = result[target.id];

    if (stored) {
      configured[target.id] = stored;
      forms[target.id] = { ...stored, cveApiKey: "" };
    } else if (instancesOf(target.id).length === 1) {
      // Only one to choose from: chosen.
      forms[target.id].instance = instancesOf(target.id)[0]!.id;
    }
  }

  loading.value = false;
}

async function onSave(target: PublicationTarget): Promise<void> {
  savingTarget.value = target;
  errors[target] = undefined;

  const form = forms[target];

  try {
    const saved = await apiRequest<StoredCredential>(
      `/cna-credentials/${target}`,
      {
        method: "PUT",
        body: JSON.stringify({
          instance: form.instance,
          shortName: form.shortName,
          orgId: form.orgId,
          cveApiOrg: form.cveApiOrg,
          cveApiUser: form.cveApiUser,
          cveApiKey: form.cveApiKey,
        }),
      },
    );

    configured[target] = saved;
    forms[target] = { ...saved, cveApiKey: "" };
  } catch (err) {
    errors[target] = err instanceof ApiError
      ? err.message
      : "Unable to save credential.";
  } finally {
    savingTarget.value = null;
  }
}

async function onDelete(target: PublicationTarget): Promise<void> {
  savingTarget.value = target;

  try {
    await apiRequest(`/cna-credentials/${target}`, { method: "DELETE" });
    delete configured[target];
    forms[target] = emptyForm();
  } finally {
    savingTarget.value = null;
  }
}

onMounted(load);
</script>

<template>
  <main class="container py-5" style="max-width: 720px;">
    <h1 class="h3 mb-4">CNA credentials</h1>

    <p class="text-secondary">
      Used by the "Vulnerability-Lookup" and "CVE Program" panels when
      reserving or publishing a CVE. Stored encrypted, per-account — not
      shared with other users.
    </p>

    <div v-if="loading" class="text-secondary">Loading…</div>

    <p v-else-if="visibleTargets.length === 0" class="text-secondary">
      No CNA publication targets are enabled on this deployment.
    </p>

    <div v-else>
      <section
        v-for="target in visibleTargets"
        :key="target.id"
        class="card mb-4"
      >
        <div class="card-body">
          <h2 class="h5 d-flex justify-content-between align-items-center">
            {{ target.label }}
            <span
              v-if="configured[target.id]"
              class="badge text-bg-success"
            >
              Configured
            </span>
            <span v-else class="badge text-bg-secondary">Not configured</span>
          </h2>

          <p
            v-if="instancesOf(target.id).length === 0"
            class="text-secondary mb-0"
          >
            This instance's operator hasn't configured a server to publish
            to yet ([[panels.{{ target.id }}.instances]] in the config).
          </p>

          <form
            v-else
            @submit.prevent="onSave(target.id)"
          >
            <div class="mb-2">
              <label
                :for="`instance-${target.id}`"
                class="form-label"
              >Server</label>
              <select
                :id="`instance-${target.id}`"
                v-model="forms[target.id].instance"
                class="form-select"
                required
              >
                <option
                  value=""
                  disabled
                >
                  Choose…
                </option>
                <option
                  v-for="instance in instancesOf(target.id)"
                  :key="instance.id"
                  :value="instance.id"
                >
                  {{ instance.name }}
                </option>
              </select>
              <div
                v-if="urlOf(target.id)"
                class="form-text"
              >
                {{ urlOf(target.id) }}
              </div>
            </div>

            <div class="row">
              <div class="col-md-6 mb-2">
                <label class="form-label">Short name</label>
                <input
                  v-model="forms[target.id].shortName"
                  type="text"
                  class="form-control"
                  required
                >
              </div>

              <div class="col-md-6 mb-2">
                <label class="form-label">Org ID</label>
                <input
                  v-model="forms[target.id].orgId"
                  type="text"
                  class="form-control"
                  required
                >
              </div>

              <div class="col-md-6 mb-2">
                <label class="form-label">CVE-API-ORG</label>
                <input
                  v-model="forms[target.id].cveApiOrg"
                  type="text"
                  class="form-control"
                  required
                >
              </div>

              <div class="col-md-6 mb-2">
                <label class="form-label">CVE-API-USER</label>
                <input
                  v-model="forms[target.id].cveApiUser"
                  type="text"
                  class="form-control"
                  required
                >
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label">CVE-API-KEY</label>
              <input
                v-model="forms[target.id].cveApiKey"
                type="password"
                class="form-control"
                :placeholder="needsKey(target.id) ? '' : 'Unchanged'"
                :required="needsKey(target.id)"
              >
              <div class="form-text">
                <template v-if="configured[target.id] && needsKey(target.id)">
                  Enter the key again for the new server.
                </template>
                <template v-else>
                  Never shown once saved — leave blank to keep the current
                  key when updating the other fields.
                </template>
              </div>
            </div>

            <div v-if="errors[target.id]" class="alert alert-danger">
              {{ errors[target.id] }}
            </div>

            <button
              type="submit"
              class="btn btn-primary"
              :disabled="savingTarget === target.id"
            >
              Save
            </button>

            <button
              v-if="configured[target.id]"
              type="button"
              class="btn btn-outline-danger ms-2"
              :disabled="savingTarget === target.id"
              @click="onDelete(target.id)"
            >
              Remove
            </button>
          </form>
        </div>
      </section>
    </div>
  </main>
</template>
