import {
  markRaw,
} from "vue";

import type {
  EditorAction,
  EditorRepository,
} from "../contracts";

import ConvertDialog from
  "./ConvertDialog.vue";

import type {
  ConvertInput,
} from "./ConvertDialog.vue";

// The profiles whose records can be converted.
const SOURCE_PROFILES = ["cve-5.2.0", "gcve-bcp-05-1.7"];

/**
 * "Convert to…": drafts a CSAF 2.1 advisory or an OSV 1.9.2 record from
 * the current CVE/GCVE record (converted by the backend, see
 * csaf_convert.py and osv_convert.py), saves it as a new private draft
 * and opens it. The source record is left as it is. Built by the page,
 * which has the repository, knows how to open a record and whether
 * leaving the current one loses unsaved changes (mayLeave asks; false
 * cancels before anything is created).
 */
export function createConvertAction(
  repository: EditorRepository,
  open: (identifier: string) => void,
  mayLeave: () => boolean = () => true,
): EditorAction {
  return {
    id: "convert",
    label: "Convert to…",

    isVisible: (context) => SOURCE_PROFILES.includes(context.profile),

    isEnabled: () => Boolean(repository.convertRecord),

    dialog: markRaw(ConvertDialog),

    async run(context, input) {
      const { target, ecosystem } = input as ConvertInput;

      if (!repository.convertRecord || !mayLeave()) {
        return;
      }

      const converted = await repository.convertRecord(
        context.record,
        context.profile,
        target,
        { ecosystem },
      );
      const created = await repository.createRecord(converted.record, converted.profile, true);

      open(created.identifier);
    },
  };
}
