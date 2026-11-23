/*
 * Bundles the <vulniverse-editor> package's public types into one
 * self-contained dist/element/vulniverse-editor.d.ts, next to the bundle
 * (run by `npm run build:element`, after Vite, which empties the folder).
 *
 * Entry: src/element.types.ts. Vue is bundled into the editor, not a
 * dependency of the package, so the one type taken from it (a panel's
 * `component`) is replaced with a local one; any other import left in
 * the output fails the build. The result is then type-checked on its own,
 * in an empty folder, the way a project without Vue installed sees it.
 */

import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const OUT = "dist/element/vulniverse-editor.d.ts";
const bin = (name) => join(process.cwd(), "node_modules", ".bin", name);

execFileSync(bin("dts-bundle-generator"), [
  "--project", "tsconfig.app.json",
  "--no-check",
  "--no-banner",
  // Keeps the HTMLElementTagNameMap entry, so createElement is typed.
  "--inline-declare-global",
  "-o", OUT,
  "src/element.types.ts",
], { stdio: "inherit" });

const VUE_IMPORT = /^import \{ Component \} from ['"]vue['"];$/m;
let types = readFileSync(OUT, "utf8");

if (!VUE_IMPORT.test(types)) {
  throw new Error(`${OUT}: the expected import of Vue's Component type is missing; update build-types.mjs.`);
}

types = types.replace(
  VUE_IMPORT,
  "/** A Vue component: an object from `defineComponent`, a single-file component, or a function. */\ntype Component = object;",
);

const imports = types.match(/^import .*$/gm);
if (imports) {
  throw new Error(`${OUT}: the types must not import anything, found:\n${imports.join("\n")}`);
}

writeFileSync(OUT, types);

// The check: strict, library checks on, nothing installed to lean on.
const folder = mkdtempSync(join(tmpdir(), "vulniverse-types-"));
try {
  writeFileSync(join(folder, "vulniverse-editor.d.ts"), types);
  execFileSync(bin("tsc"), [
    "--noEmit", "--strict", "--skipLibCheck", "false",
    "--target", "es2022", "--module", "esnext", "--moduleResolution", "bundler",
    "--lib", "es2022,dom",
    "vulniverse-editor.d.ts",
  ], { stdio: "inherit", cwd: folder });
} finally {
  rmSync(folder, { recursive: true, force: true });
}

console.log(`${OUT}: ${types.split("\n").length} lines, self-contained.`);
