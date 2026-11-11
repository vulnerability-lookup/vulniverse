import type { JsonSchema } from "@jsonforms/core";
import { describe, expect, it } from "vitest";

import authoringSchema from "@/generated/schemas/csaf-2.1/authoring.schema.json";
import cveSchema from "@/generated/schemas/cve-5.2.0/authoring.schema.json";

import { cvssObject, cvssVersions, extraFields, prefixVersion, versionOf } from "../cvss";

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- generated JSON
const content = (authoringSchema as any).properties.vulnerabilities.items.properties.metrics
  .items.properties.content.properties as Record<string, JsonSchema>;

describe("cvssVersions", () => {
  it("reads the versions of CSAF's CVSS schemas", () => {
    expect(cvssVersions(content.cvss_v2)).toEqual(["2.0"]);
    expect(cvssVersions(content.cvss_v3)).toEqual(["3.0", "3.1"]);
    expect(cvssVersions(content.cvss_v4)).toEqual(["4.0"]);
  });

  it("matches nothing else", () => {
    expect(cvssVersions(content.epss)).toEqual([]);
    expect(cvssVersions(content.ssvc_v2)).toEqual([]);
    expect(cvssVersions(cveSchema as JsonSchema)).toEqual([]);
  });
});

describe("prefixVersion", () => {
  it("reads an allowed version from a pasted vector's prefix", () => {
    expect(prefixVersion("CVSS:3.0/AV:N/AC:L", ["3.0", "3.1"])).toBe("3.0");
    expect(prefixVersion("CVSS:4.0/AV:N", ["3.0", "3.1"])).toBeUndefined();
    expect(prefixVersion("AV:N/AC:L/Au:N", ["2.0"])).toBeUndefined();
  });
});

describe("versionOf", () => {
  it("prefers the stored version, then the vector prefix, then the newest", () => {
    expect(versionOf({ version: "3.0" }, ["3.0", "3.1"])).toBe("3.0");
    expect(versionOf({ vectorString: "CVSS:3.0/AV:N" }, ["3.0", "3.1"])).toBe("3.0");
    expect(versionOf(undefined, ["3.0", "3.1"])).toBe("3.1");
  });
});

describe("cvssObject", () => {
  it("computes score and severity from a complete vector", () => {
    expect(cvssObject("3.1", "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", undefined)).toEqual({
      version: "3.1",
      vectorString: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
      baseScore: 9.8,
      baseSeverity: "CRITICAL",
    });
    expect(cvssObject("2.0", "AV:N/AC:L/Au:N/C:P/I:P/A:P", undefined)).toEqual({
      version: "2.0",
      vectorString: "AV:N/AC:L/Au:N/C:P/I:P/A:P",
      baseScore: 7.5,
    });
  });

  it("keeps the previous score while the vector is incomplete and drops per-metric fields", () => {
    const previous = { version: "3.1", vectorString: "x", baseScore: 6.1, baseSeverity: "MEDIUM", attackVector: "LOCAL" };

    expect(extraFields(previous)).toEqual(["attackVector"]);
    expect(cvssObject("3.1", "CVSS:3.1/AV:N", previous)).toEqual({
      version: "3.1",
      vectorString: "CVSS:3.1/AV:N",
      baseScore: 6.1,
      baseSeverity: "MEDIUM",
    });
  });
});
