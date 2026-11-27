import { describe, expect, it } from "vitest";

import { editorAjv } from "../../core/ajv";
import { getEditorProfile, STANDALONE_PROFILES, SUPPORTED_PROFILES } from "..";

const complete = {
  id: "EUVD-2026-1234",
  title: "Buffer overflow in Widget",
  description: "A crafted packet overflows a buffer in Widget.",
  base_score: 7.5,
  base_score_version: "3.1",
  base_score_vector: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
  references: ["https://example.org/advisory/1"],
  affected: [{ vendor: "Acme", product: "Widget", version: "< 2.0" }],
};

describe("the EUVD profile", () => {
  const profile = getEditorProfile("euvd-1.0");
  const validate = editorAjv.compile(profile.schema);

  it("is offered with the other formats", () => {
    expect(SUPPORTED_PROFILES.map(({ id }) => id)).toContain("euvd-1.0");
  });

  it("is not offered for new records in the standalone app, which cannot reserve an EUVD ID", () => {
    const standalone = STANDALONE_PROFILES.map(({ id }) => id);
    expect(standalone).not.toContain("euvd-1.0");
    expect(standalone).toEqual(
      SUPPORTED_PROFILES.map(({ id }) => id).filter((id) => id !== "euvd-1.0"),
    );
  });

  it("accepts a CVSS 2.0 vector, which has no prefix", () => {
    expect(
      validate({ ...complete, base_score_version: "2.0", base_score_vector: "AV:N/AC:L/Au:N/C:P/I:P/A:P" }),
    ).toBe(true);
  });

  it("starts a record without an identifier, which the EUVD reserves", () => {
    expect(profile.createEmptyDocument()).not.toHaveProperty("id");
  });

  it("accepts a complete record", () => {
    expect(validate(complete)).toBe(true);
  });

  it.each([
    { ...complete, title: "" },
    { ...complete, id: "CVE-2026-1234" },
    { ...complete, references: ["ftp://example.org/x"] },
    { ...complete, affected: [{ vendor: "Acme" }] },
    { ...complete, base_score: 11 },
    { ...complete, base_score_version: "5.0" },
    { title: "Scored without a version", base_score: 7.5 },
    { ...complete, base_score_vector: "CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N" },
    { ...complete, base_score_vector: "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N" },
    { ...complete, base_score_version: "4.0", base_score_vector: "CVSS:3.1/AV:N" },
    { ...complete, unknown: true },
  ])("refuses what Vulnerability-Lookup would refuse: %j", (record) => {
    expect(validate(record)).toBe(false);
  });
});
