import { describe, expect, it } from "vitest";

import { diffLines, foldUnchanged } from "../line-diff";

const kinds = (before: string[], after: string[]) =>
  diffLines(before, after).map((line) => `${line.kind[0]} ${line.text}`);

describe("diffLines", () => {
  it("shows an edited line as removed, then added", () => {
    expect(kinds(["{", "a: 1", "}"], ["{", "a: 2", "}"])).toEqual(["s {", "r a: 1", "a a: 2", "s }"]);
  });

  it("finds inserted and removed lines in the middle", () => {
    expect(kinds(["a", "b", "c", "d"], ["a", "x", "b", "d"])).toEqual(["s a", "a x", "s b", "r c", "s d"]);
  });

  it("numbers lines in both texts", () => {
    const [first, removed, added, last] = diffLines(["a", "b", "c"], ["a", "B", "c"]);

    expect([first!.oldNumber, first!.newNumber]).toEqual([1, 1]);
    expect([removed!.oldNumber, removed!.newNumber]).toEqual([2, undefined]);
    expect([added!.oldNumber, added!.newNumber]).toEqual([undefined, 2]);
    expect([last!.oldNumber, last!.newNumber]).toEqual([3, 3]);
  });

  it("finds nothing in equal texts", () => {
    expect(diffLines(["a", "b"], ["a", "b"]).every((line) => line.kind === "same")).toBe(true);
  });
});

describe("foldUnchanged", () => {
  it("folds unchanged lines away from changes, keeping some around them", () => {
    const before = Array.from({ length: 20 }, (_, index) => `line ${index}`);
    const after = before.map((line, index) => (index === 10 ? "changed" : line));
    const rows = foldUnchanged(diffLines(before, after), 2);

    expect(rows.map((row) => (row.type === "gap" ? `gap ${row.lines.length}` : row.line.text))).toEqual([
      "gap 8", "line 8", "line 9", "line 10", "changed", "line 11", "line 12", "gap 7",
    ]);
  });
});
