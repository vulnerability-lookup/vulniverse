<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";

import { apiRequest } from "@/repositories/apiRequest";
import { RepositoryError } from "@/repositories/RepositoryError";
import type { PublicationTarget } from "@/editor/contracts";

interface TargetInfo {
  id: PublicationTarget;
  label: string;
}

const TARGETS: TargetInfo[] = [
  { id: "vl", label: "Vulnerability-Lookup" },
  { id: "cve-program", label: "CVE Program" },
];

interface StoredCredential {
  cveUrl: string;
  shortName: string;
  orgId: string;
  cveApiOrg: string;
  cveApiUser: string;
}

interface FormState {
  cveUrl: string;
  shortName: string;
  orgId: string;
  cveApiOrg: string;
  cveApiUser: string;
  cveApiKey: string;
}

function emptyForm(): FormState {
  return {
    cveUrl: "",
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

async function load(): Promise<void> {
  loading.value = true;

  const result = await apiRequest<Record<string, StoredCredential>>(
    "/cna-credentials",
  );

  for (const target of TARGETS) {
    const stored = result[target.id];

    if (stored) {
      configured[target.id] = stored;
      forms[target.id] = { ...stored, cveApiKey: "" };
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
          cveUrl: form.cveUrl,
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
    errors[target] = err instanceof RepositoryError
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

    <div v-else>
      <section
        v-for="target in TARGETS"
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

          <form @submit.prevent="onSave(target.id)">
            <div class="mb-2">
              <label class="form-label">CVE API URL</label>
              <input
                v-model="forms[target.id].cveUrl"
                type="url"
                class="form-control"
                required
              >
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
                :placeholder="configured[target.id] ? 'Unchanged' : ''"
                :required="!configured[target.id]"
              >
              <div class="form-text">
                Never shown once saved — leave blank to keep the current
                key when updating the other fields.
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
