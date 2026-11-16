/*
 * The editor tutorial: each step points at an element (a CSS selector inside
 * the editor) and may first switch to a section. A step whose element
 * isn't there (a host without that button, a panel not enabled) is
 * skipped, so the same steps work in the standalone app, the sandbox
 * and an embedding host like Vulnerability-Lookup.
 */
export interface TutorialStep {
  title: string;
  text: string;
  // Section to show first ("editor", "tree", …); unchanged when absent.
  section?: string;
  // Element to highlight; a step without one is a centred note.
  target?: string;
}

export const TUTORIAL_STEPS: TutorialStep[] = [
  {
    title: "Welcome",
    text: "This short tutorial shows the main parts of the editor. Use the arrow keys or the buttons to move through it, Esc to leave.",
  },
  {
    title: "The record",
    target: ".editor-header-main",
    text: "What you are editing: its identifier, the profile (record format) it is checked against, and badges for draft state and unsaved changes.",
  },
  {
    title: "Actions",
    target: "[data-tutorial='actions']",
    text: "Reload discards unsaved changes, Validate checks the record, Save keeps it. Publish and the other buttons move it through its lifecycle; Download saves it as JSON, an HTML page or a PDF.",
  },
  {
    title: "Sections",
    target: "nav.editor-sidebar",
    text: "Switch between the form (Editor), an overview of the whole record (Tree), a read-only Preview and the raw JSON. Panels below add tools such as templates or lookups.",
  },
  {
    title: "Tabs",
    section: "editor",
    target: ".editor-content .categorization-category",
    text: "The form is split into tabs by topic. Each tab only shows its own fields; nothing is lost by switching.",
  },
  {
    title: "Fields",
    section: "editor",
    target: ".editor-content [data-path]",
    text: "Each field has a short description. Fields marked * are required. Problems found while typing show right at the field.",
  },
  {
    title: "Validation",
    target: "[aria-label='Editor actions']",
    text: "Validate checks the whole record against its schema. Errors are listed with the field they concern; click one to jump straight to that field.",
  },
  {
    title: "Tree",
    section: "tree",
    target: ".editor-content .record-graph-toolbar",
    text: "The Tree shows every field of the record. Click a circle to open it, a name to jump to the field. Search by name or value, zoom with the buttons or Ctrl + wheel. Red rings lead to errors, dashed red circles are required fields still missing.",
  },
  {
    title: "Preview",
    section: "preview",
    target: ".editor-content",
    text: "A read-only rendering of the record as currently edited: what Download exports as an HTML page or PDF.",
  },
  {
    title: "Advanced JSON",
    section: "json",
    target: ".editor-content",
    text: "Edit or paste the raw JSON. Changes reach the form only once you apply them.",
  },
  {
    title: "Done",
    section: "editor",
    text: "That's it. Start this tutorial again any time with the Tutorial button in the header.",
  },
];
