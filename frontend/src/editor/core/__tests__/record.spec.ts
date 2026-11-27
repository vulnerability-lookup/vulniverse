import { describe, expect, it } from "vitest";

import { withGenerator } from "../record";

describe("withGenerator", () => {
  it("sets x_generator in the CNA container without touching the input", () => {
    const record = {
      dataType: "CVE_RECORD",
      containers: { cna: { title: "T", x_generator: { engine: "Vulnogram 0.2.0" } }, adp: [] },
    };

    const stamped = withGenerator(record);

    expect(stamped.containers).toEqual({
      cna: { title: "T", x_generator: { engine: `Vulniverse v${__VULNIVERSE_VERSION__}` } },
      adp: [],
    });
    expect(record.containers.cna.x_generator).toEqual({ engine: "Vulnogram 0.2.0" });
  });

  it("leaves records without a CNA container alone (OSV)", () => {
    const osv = { id: "OSV-1", affected: [] };

    expect(withGenerator(osv)).toBe(osv);
  });
});
