import type {
  CveRecord,
  EditorAction,
  EditorContext,
} from "../contracts";

import {
  getGcveVulnId,
} from "../gcve";

import {
  printPage,
  recordPage,
} from "./record-page";

/**
 * Saves the current record as it is in the editor (unsaved changes
 * included) in the format picked from the button's menu: the raw JSON,
 * a standalone HTML page of its preview, or that page through the
 * browser's print dialog, where "Save as PDF" makes the PDF. Entirely
 * client-side, no repository/backend involvement.
 */
export const downloadAction: EditorAction = {
  id: "download",
  label: "Download",

  options: [
    { id: "json", label: "JSON" },
    { id: "html", label: "HTML page" },
    { id: "pdf", label: "PDF (print dialog)" },
  ],

  async run(context, format = "json") {
    const name = recordName(context);

    if (format === "json") {
      saveFile(JSON.stringify(context.record, null, 2), "application/json", `${name}.json`);
      return;
    }

    const page = await recordPage(context, name);

    if (format === "html") {
      saveFile(page, "text/html", `${name}.html`);
    } else {
      printPage(page);
    }
  },
};

/**
 * What to call the file: the record's own vulnerability ID (GCVE, CVE
 * or OSV), which a new, unsaved record already has, else its storage
 * identifier.
 */
export function recordName(context: EditorContext): string {
  const record = context.record as CveRecord & { id?: unknown };
  const candidates = [getGcveVulnId(record), record.cveMetadata?.cveId, record.id, context.identifier];
  const name = candidates.find((value): value is string => typeof value === "string" && value.length > 0);

  // Keep it a safe file name whatever the ID holds.
  return name ? name.replace(/[^\w.-]+/g, "_") : "record";
}

function saveFile(content: string, type: string, name: string): void {
  const url = URL.createObjectURL(new Blob([content], { type }));

  try {
    const link = document.createElement("a");

    link.href = url;
    link.download = name;
    link.click();
  } finally {
    URL.revokeObjectURL(url);
  }
}
