import { describe, expect, it, vi } from "vitest";

import type { EditorContext, EditorRepository } from "../../contracts";
import { createConvertAction } from "../convert";

const context = (profile: string): EditorContext => ({
  identifier: "7", profile, record: { cveMetadata: { cveId: "CVE-2026-12345" } }, isDraft: false,
});

function repository() {
  return {
    convertRecord: vi.fn<(record: unknown, profile: string, target: string, options: unknown) => Promise<unknown>>(
      async (_record, _profile, target) => ({
        record: { converted: target }, profile: target === "osv" ? "osv-1.9.2" : "csaf-2.1",
      }),
    ),
    createRecord: vi.fn<(record: unknown, profile: string, isDraft: boolean) => Promise<unknown>>(
      async (record, profile, isDraft) => ({ identifier: "42", profile, record, isDraft }),
    ),
  } as unknown as EditorRepository & {
    convertRecord: ReturnType<typeof vi.fn>;
    createRecord: ReturnType<typeof vi.fn>;
  };
}

describe("createConvertAction", () => {
  it("is offered on CVE and GCVE records, with a dialog", () => {
    const action = createConvertAction(repository(), () => {});

    expect(["cve-5.2.0", "gcve-bcp-05-1.7", "osv-1.9.2", "csaf-2.1"].map((p) => action.isVisible?.(context(p))))
      .toEqual([true, true, false, false]);
    expect(action.dialog).toBeDefined();
  });

  it.each([
    ["csaf", "", "csaf-2.1"],
    ["osv", "PyPI", "osv-1.9.2"],
  ])("converts to %s, saves a private draft and opens it", async (target, ecosystem, profile) => {
    const repo = repository();
    const open = vi.fn<(identifier: string) => void>();

    await createConvertAction(repo, open).run(context("gcve-bcp-05-1.7"), { target, ecosystem });

    expect(repo.convertRecord).toHaveBeenCalledWith(
      context("gcve-bcp-05-1.7").record, "gcve-bcp-05-1.7", target, { ecosystem },
    );
    expect(repo.createRecord).toHaveBeenCalledWith({ converted: target }, profile, true);
    expect(open).toHaveBeenCalledWith("42");
  });

  it("creates nothing when leaving the record is declined", async () => {
    const repo = repository();
    const open = vi.fn<(identifier: string) => void>();

    await createConvertAction(repo, open, () => false).run(context("cve-5.2.0"), { target: "osv", ecosystem: "" });

    expect(repo.convertRecord).not.toHaveBeenCalled();
    expect(repo.createRecord).not.toHaveBeenCalled();
    expect(open).not.toHaveBeenCalled();
  });
});
