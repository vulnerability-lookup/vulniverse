import {
  downloadJsonModule,
} from "./download-json";

import type {
  EditorModule,
} from "../contracts";

/*
 * One file per module (mirrors editor/renderers/index.ts). To add a
 * new one: create modules/<id>.ts exporting an EditorModule, then
 * list it here. Hosts opt in by passing some subset of this list (or
 * their own modules entirely) to VulniverseEditor's `modules` prop —
 * nothing here is wired up automatically.
 */
export const BUILTIN_MODULES: EditorModule[] = [
  downloadJsonModule,
];

export { downloadJsonModule };
