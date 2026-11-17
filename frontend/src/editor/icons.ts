/*
 * Line icons for the editor's sidebar (sections and panels), as the `d`
 * of one SVG path on a 16×16 grid, drawn as a stroke — the same form as
 * EditorAction.icon and EditorPanel.icon, which a host can set too.
 */
export const ICONS = {
  // Pencil.
  editor: "M11 2.5l2.5 2.5L5.5 13H3v-2.5L11 2.5ZM9.5 4l2.5 2.5",
  // Branches from a root to two nodes.
  tree: "M2 8a1 1 0 1 0 2 0a1 1 0 1 0-2 0M4 8h1.5c2 0 2-4 4-4H11M5.5 8c2 0 2 4 4 4H11M11 4a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0M11 12a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0",
  // Eye.
  preview: "M1.5 8S4 3.5 8 3.5 14.5 8 14.5 8 12 12.5 8 12.5 1.5 8 1.5 8ZM8 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z",
  // Curly braces.
  json: "M5.5 2.5c-1.5 0-2 .7-2 2v1.3c0 1-.5 1.7-1.5 2.2 1 .5 1.5 1.2 1.5 2.2v1.3c0 1.3.5 2 2 2M10.5 2.5c1.5 0 2 .7 2 2v1.3c0 1 .5 1.7 1.5 2.2-1 .5-1.5 1.2-1.5 2.2v1.3c0 1.3-.5 2-2 2",
  // Two stacked sheets.
  templates: "M5.5 5.5h7v8h-7ZM3.5 10.5v-8h7",
  // Magnifier.
  lookup: "M7 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10ZM10.5 10.5l3.5 3.5",
  // Shield.
  publish: "M8 1.5l5.5 2v4c0 3.5-2.4 6-5.5 7-3.1-1-5.5-3.5-5.5-7v-4L8 1.5Z",
  // Check in a circle.
  quality: "M8 14.5A6.5 6.5 0 1 0 8 1.5a6.5 6.5 0 0 0 0 13ZM5.5 8.2l1.7 1.7 3.3-3.4",
  // Git branch.
  patch: "M5 2.5V9M5 9a2 2 0 1 0 0 4 2 2 0 0 0 0-4ZM11 3a2 2 0 1 0 0 4 2 2 0 0 0 0-4ZM11 7c0 2.5-2 3-6 4",
  // Bar chart.
  stats: "M2.5 13.5h11M4.5 11V8M8 11V4M11.5 11V6.5",
  // A window: for a host panel without an icon of its own.
  panel: "M2.5 2.5h11v11h-11ZM2.5 6h11",
  // Chevron pointing left: collapse the sidebar (turned for expand).
  collapse: "M10 3.5 5.5 8l4.5 4.5",
} as const;
