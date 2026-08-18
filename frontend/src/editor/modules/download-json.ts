import type {
  EditorModule,
} from "../contracts";

/**
 * Saves the current record's JSON to a local file. Entirely
 * client-side — no repository/backend involvement — so it's a good
 * template for a new module file: copy this one, change `id`/`label`,
 * and implement `run()`.
 */
export const downloadJsonModule: EditorModule = {
  id: "download-json",
  label: "Download JSON",

  async run(context) {
    const blob = new Blob(
      [JSON.stringify(context.record, null, 2)],
      { type: "application/json" },
    );

    const url = URL.createObjectURL(blob);

    try {
      const link = document.createElement("a");

      link.href = url;
      link.download = `${context.identifier || "record"}.json`;
      link.click();
    } finally {
      URL.revokeObjectURL(url);
    }
  },
};
