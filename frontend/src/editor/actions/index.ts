import {
  downloadJsonAction,
} from "./download-json";

import type {
  EditorAction,
} from "../contracts";

/*
 * One file per action (mirrors editor/renderers/index.ts). To add a
 * new one: create actions/<id>.ts exporting an EditorAction, then
 * list it here. Hosts opt in by passing some subset of this list (or
 * their own actions entirely) to VulniverseEditor's `actions` prop —
 * nothing here is wired up automatically.
 */
export const BUILTIN_ACTIONS: EditorAction[] = [
  downloadJsonAction,
];

export { downloadJsonAction };
