export interface SupportedProfile {
  id: string;
  label: string;
  description: string;
}

/*
 * The two profiles Vulniverse currently generates editor schemas
 * for (schemas/manifest.json declares others' base schemas but
 * only these two have generated authoring/ui schema pairs — see
 * scripts/generate_editor_schemas.py and schemas/editor/).
 */
export const SUPPORTED_PROFILES: SupportedProfile[] = [
  {
    id: "cve-5.2.0",
    label: "CVE",
    description: "A standard CVE Record Format 5.2.0 record.",
  },
  {
    id: "gcve-bcp-05-1.7",
    label: "GCVE",
    description:
      "A CVE record extended with the GCVE-BCP-05 x_gcve extension.",
  },
];

export const DEFAULT_PROFILE_ID = SUPPORTED_PROFILES[0]!.id;
