import { describe, expect, it } from "vitest";

import { csaf21Profile } from "../csaf-2.1";
import { isDraftVersion, isReleased, nextVersion, releaseCsaf, versioning } from "../csaf-release";
import { resolveLifecycleTransitions } from "../../core/lifecycle";

const NOW = "2026-11-13T10:42:07.123Z";

function draft(version = "0.3.0", history = ["0.1.0", "0.2.0", "0.3.0"]) {
  return {
    document: {
      title: "Example",
      tracking: {
        id: "EX-2026-0001",
        status: "draft",
        version,
        initial_release_date: "2026-11-01T00:00:00Z",
        current_release_date: "2026-11-10T00:00:00Z",
        revision_history: history.map((number, index) => ({
          number, date: `2026-11-0${index + 1}T00:00:00Z`, summary: `Draft ${number}.`,
        })),
      },
    },
  };
}

const tracking = (document: unknown) => (document as ReturnType<typeof draft>).document.tracking;

describe("versions", () => {
  it("tells drafts from released versions", () => {
    expect(["0", "0.3.0", "1.0.0-rc.1", "2.1.0-beta"].map(isDraftVersion)).toEqual([true, true, true, true]);
    expect(["1", "1.0.0", "2.40.0+21AF26D3", "1.0.0+build-1"].map(isDraftVersion)).toEqual([false, false, false, false]);
  });

  it("computes the next version", () => {
    expect(nextVersion("0.3.0", "initial")).toBe("1.0.0");
    expect(nextVersion("1.4.2", "patch")).toBe("1.4.3");
    expect(nextVersion("1.4.2", "minor")).toBe("1.5.0");
    expect(nextVersion("1.4.2", "major")).toBe("2.0.0");
    expect(nextVersion("1.4.2+build", "patch")).toBe("1.4.3");
    expect(nextVersion("0", "initial")).toBe("1");
    expect(nextVersion("3", "minor")).toBe("4");
  });

  it("detects the versioning scheme", () => {
    expect(versioning(draft("0"))).toBe("integer");
    expect(versioning(draft())).toBe("semantic");
  });
});

describe("releaseCsaf", () => {
  it("first release: 1.0.0, one history entry instead of the drafts, all dates equal", () => {
    const released = releaseCsaf(draft(), { kind: "initial", status: "final", summary: "Initial release." }, NOW);

    expect(tracking(released)).toEqual({
      id: "EX-2026-0001",
      status: "final",
      version: "1.0.0",
      initial_release_date: "2026-11-13T10:42:07Z",
      current_release_date: "2026-11-13T10:42:07Z",
      revision_history: [{ number: "1.0.0", date: "2026-11-13T10:42:07Z", summary: "Initial release." }],
    });
    expect(isReleased(released)).toBe(true);
    expect(isReleased(draft())).toBe(false);
  });

  it("update: next version appended, initial release date kept", () => {
    const first = releaseCsaf(draft(), { kind: "initial", status: "final", summary: "Initial release." }, NOW);
    const second = releaseCsaf(first, { kind: "minor", status: "interim", summary: "Added fix." }, "2026-11-20T08:00:00Z");

    expect(tracking(second)).toMatchObject({
      status: "interim",
      version: "1.1.0",
      initial_release_date: "2026-11-13T10:42:07Z",
      current_release_date: "2026-11-20T08:00:00Z",
    });
    expect(tracking(second).revision_history.map((entry) => entry.number)).toEqual(["1.0.0", "1.1.0"]);
  });

  it("integer versioning", () => {
    const released = releaseCsaf(draft("0", ["0"]), { kind: "initial", status: "final", summary: "First." }, NOW);
    const next = releaseCsaf(released, { kind: "major", status: "final", summary: "Second." }, NOW);

    expect(tracking(next).revision_history.map((entry) => entry.number)).toEqual(["1", "2"]);
  });

  it("leaves the input untouched", () => {
    const original = draft();
    releaseCsaf(original, { kind: "initial", status: "final", summary: "x" }, NOW);

    expect(original).toEqual(draft());
  });
});

describe("CSAF lifecycle", () => {
  const ids = (record: unknown, isDraft: boolean) => resolveLifecycleTransitions(
    undefined, csaf21Profile.lifecycleTransitions, csaf21Profile.replacesDefaultTransitions,
  ).filter((t) => t.isVisible?.({ identifier: "1", profile: "csaf-2.1", record: record as never, isDraft }) ?? true)
    .map((t) => t.id);

  const released = releaseCsaf(draft(), { kind: "initial", status: "final", summary: "x" }, NOW);

  it("replaces Publish/Revert with CSAF's own steps", () => {
    expect(ids(draft(), true)).toEqual(["csaf-share-draft", "csaf-release"]);
    expect(ids(draft(), false)).toEqual(["csaf-make-private", "csaf-release"]);
    expect(ids(released, false)).toEqual(["csaf-make-private", "csaf-update"]);
    expect(ids(released, true)).toEqual(["csaf-share", "csaf-update"]);
  });

  it("warns before saving changes to a shared, released advisory only", () => {
    const warn = (record: unknown, isDraft: boolean) => csaf21Profile.saveWarning?.({
      identifier: "1", profile: "csaf-2.1", record: record as never, isDraft,
    });

    expect(warn(released, false)).toMatch(/released/);
    expect(warn(released, true)).toBeNull();
    expect(warn(draft(), false)).toBeNull();
  });
});
