import { describe, expect, it } from "vitest";

import type { MlResult } from "../result-cache";
import { recallResult, rememberResult } from "../result-cache";

function result(identifier: string | null): MlResult {
  return {
    identifier,
    description: "SQL injection",
    severity: { severity: "High", confidence: 0.8 },
    techniques: [],
    attackModel: null,
    selected: new Set(),
  };
}

describe("result cache", () => {
  it("returns the result to the same editor and record", () => {
    const editor = {};
    rememberResult(editor, result("rec-1"));

    expect(recallResult(editor, "rec-1")?.description).toBe("SQL injection");
    expect(recallResult({}, "rec-1")).toBeNull();
  });

  it("keeps an unsaved record's result after its first save", () => {
    const editor = {};
    rememberResult(editor, result(null));

    expect(recallResult(editor, null)).not.toBeNull();
    expect(recallResult(editor, "rec-1")).not.toBeNull();
  });

  it("drops it when the editor shows another record", () => {
    const editor = {};
    rememberResult(editor, result("rec-1"));

    expect(recallResult(editor, "rec-2")).toBeNull();
  });
});
