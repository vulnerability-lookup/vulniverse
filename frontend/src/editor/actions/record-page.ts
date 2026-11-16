import {
  createApp,
  nextTick,
  toRaw,
} from "vue";

import type {
  EditorContext,
} from "../contracts";

import {
  editorStateKey,
} from "../core/context/keys";

import {
  useEditorState,
} from "../core/state";

import {
  getEditorProfile,
} from "../profiles";

import GenericPreviewSection from "../sections/GenericPreviewSection.vue";

function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (char) => `&#${char.charCodeAt(0)};`);
}

/*
 * The record's preview (each profile's previewComponent, the same one
 * the Preview section shows) rendered off-screen into a standalone HTML
 * page with the editor's styles inlined, so it opens anywhere and
 * prints well.
 */
export async function recordPage(context: EditorContext, name: string): Promise<string> {
  const profile = getEditorProfile(context.profile);
  const state = useEditorState();

  state.record.value = structuredClone(toRaw(context.record));
  state.profile.value = context.profile;

  const host = document.createElement("div");
  const app = createApp(profile.previewComponent ?? GenericPreviewSection);

  app.provide(editorStateKey, state);
  app.mount(host);
  await nextTick();

  // Paper can't be clicked open, and the page brings its own heading.
  host.querySelectorAll("details").forEach((details) => { details.open = true; });
  host.querySelector("section > header")?.remove();

  const body = host.innerHTML;

  app.unmount();

  // Loaded only when exporting, so the app bundle doesn't carry the CSS twice.
  const [{ default: bootstrapCss }, { default: editorCss }] = await Promise.all([
    import("../styles/editor-bootstrap.scss?inline"),
    import("../styles/editor.scss?inline"),
  ]);

  const title = escapeHtml(name);
  const exported = new Date().toISOString().slice(0, 10);

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src * data:">
<title>${title}</title>
<style>${bootstrapCss}</style>
<style>${editorCss}</style>
<style>
  body { background: #fff; }
  .vulniverse-editor { height: auto; max-width: 60rem; margin: 2rem auto; padding: 0 1rem; display: block; border: 0; border-radius: 0; overflow: visible; }
  .record-export-footer { margin-top: 2rem; color: #6c757d; font-size: 0.8125rem; }
  @media print {
    @page { margin: 1.5cm; }
    .vulniverse-editor { max-width: none; margin: 0; padding: 0; }
    body { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
    .card-header, h1, h2, h3, h4, h5 { break-after: avoid; }
    tr, li, .badge { break-inside: avoid; }
    a { color: inherit; }
  }
</style>
</head>
<body>
<main class="vulniverse-editor">
<h1 class="h3 mb-4">${title}</h1>
${body}
<footer class="record-export-footer">${escapeHtml(profile.label)} record, exported from Vulniverse on ${exported}.</footer>
</main>
</body>
</html>
`;
}

/**
 * Opens the browser's print dialog for `html` (where the user can pick
 * "Save as PDF"), from a hidden, sandboxed frame that is removed again
 * once printing is done.
 */
export function printPage(html: string): void {
  const frame = document.createElement("iframe");

  // No scripts in the page; same-origin only so print() can be called on it.
  frame.setAttribute("sandbox", "allow-same-origin allow-modals");
  frame.setAttribute("aria-hidden", "true");
  frame.style.cssText = "position: fixed; right: 0; bottom: 0; width: 0; height: 0; border: 0;";
  frame.srcdoc = html;

  frame.addEventListener("load", () => {
    const view = frame.contentWindow;

    view?.addEventListener("afterprint", () => frame.remove());
    view?.focus();
    view?.print();
  }, { once: true });

  document.body.append(frame);
}
