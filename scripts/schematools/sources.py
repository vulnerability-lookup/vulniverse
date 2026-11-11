"""The upstream schema sources Vulniverse vendors, one entry per format.

A :class:`SchemaSource` says where a format's schema comes from, which files
to copy into ``schemas/upstream/``, how to recognise the right schema, and
how to write its profile into ``schemas/manifest.json``. Adding a format
means adding one entry to :data:`SOURCES`; the command-line options
(``--<name>-ref`` and so on) and the update steps follow from it.
"""

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from .errors import UpdateError
from .jsontypes import JsonObject, as_dict

UPSTREAM = Path("upstream")


@dataclass(frozen=True)
class SchemaSource:
    """One upstream schema source.

    ``files`` maps a version to ``{path in the repository: path below
    schemas/}``; its first entry is the format's main schema, the one
    ``check`` inspects and the profile's ``baseSchema`` names. ``profile``
    builds the manifest entry from the existing one and the version of every
    source (GCVE builds on the CVE version, OSV on the GCVE one).
    """

    name: str
    # The upstream repository's short name, for --help.
    title: str
    version_help: str
    repository: str
    default_ref: str
    default_version: str
    profile_id: Callable[[str], str]
    files: Callable[[str], dict[Path, Path]]
    check: Callable[[JsonObject, str], None]
    profile: Callable[[JsonObject, Mapping[str, str]], JsonObject]
    # Only CVE: older releases publish the bundled schema elsewhere.
    main_file_option: bool = False

    def main_file(self, version: str) -> tuple[Path, Path]:
        """(path in the repository, path below schemas/) of the main schema."""
        return next(iter(self.files(version).items()))

    def base_schema(self, version: str) -> str:
        return self.main_file(version)[1].as_posix()


def _existing(profiles: JsonObject, profile_id: str) -> JsonObject:
    # A copy: the builders may remove stale keys before merging.
    return dict(as_dict(profiles.get(profile_id)))


# --- CVE --------------------------------------------------------------------

CVE_SCHEMA_SOURCE = Path("schema/docs/CVE_Record_Format_bundled.json")


def cve_profile_id(version: str) -> str:
    return f"cve-{version}"


def cve_files(version: str, source: Path = CVE_SCHEMA_SOURCE) -> dict[Path, Path]:
    return {source: UPSTREAM / "cve" / version / "CVE_Record_Format_bundled.json"}


def check_cve_schema(schema: JsonObject, version: str) -> None:
    schema_uri = schema.get("$schema")

    if not isinstance(schema_uri, str) or "draft-07" not in schema_uri:
        raise UpdateError(
            "The selected CVE file does not look like the expected "
            "Draft-07 CVE Record Format schema."
        )

    if schema.get("title") != "CVE JSON record format":
        raise UpdateError(f"Unexpected CVE schema title: {schema.get('title')!r}")

    definitions = schema.get("definitions")

    if not isinstance(definitions, dict):
        raise UpdateError("The CVE schema has no 'definitions' object.")

    data_version = definitions.get("dataVersion")

    if not isinstance(data_version, dict):
        raise UpdateError("The CVE schema has no definitions.dataVersion object.")

    declared = data_version.get("default")

    # CVE 5.0 uses a single-value enum instead of default.
    enum_values = data_version.get("enum")
    if declared is None and isinstance(enum_values, list) and len(enum_values) == 1:
        declared = enum_values[0]

    if declared != version:
        raise UpdateError(
            f"CVE version mismatch: --cve-version={version!r}, "
            f"but the selected schema declares dataVersion={declared!r}."
        )


def cve_profile(existing: JsonObject, versions: Mapping[str, str]) -> JsonObject:
    version = versions["cve"]
    profile = {
        **existing,
        "kind": "cve",
        "label": existing.get("label", f"CVE {version}"),
        "version": version,
        "baseSchema": CVE.base_schema(version),
    }
    # Provenance metadata of the previous updater; no longer written.
    profile.pop("sourceMetadata", None)
    profile.setdefault(
        "editor",
        {
            "layout": "editor/cve.layout.json",
            "variant": "Published",
            "autoAdditionalPropertiesFrom": "containers.cna",
        },
    )
    profile.setdefault("validation", {"preferredRootBranch": {"keyword": "oneOf", "index": 0}})
    profile.setdefault("identifier", {"strategy": "cve"})
    return profile


CVE = SchemaSource(
    name="cve",
    version_help="CVE Record Format version.",
    title="CVEProject/cve-schema",
    repository="https://github.com/CVEProject/cve-schema.git",
    default_ref="v5.2.0",
    default_version="5.2.0",
    profile_id=cve_profile_id,
    files=cve_files,
    check=check_cve_schema,
    profile=cve_profile,
    main_file_option=True,
)


# --- GCVE (GCVE-BCP-05, an extension of CVE records) -------------------------


def gcve_profile_id(version: str) -> str:
    return f"gcve-bcp-05-{version}"


def gcve_files(version: str) -> dict[Path, Path]:
    return {
        Path("bcp-05/schema/gcve-bcp-05.schema.json"): (
            UPSTREAM / "gcve" / "bcp-05" / version / "gcve-bcp-05.schema.json"
        )
    }


def check_gcve_schema(schema: JsonObject, version: str) -> None:
    schema_id = schema.get("$id")

    if not isinstance(schema_id, str) or "gcve-bcp-05" not in schema_id:
        raise UpdateError(f"Unexpected GCVE schema identifier: {schema_id!r}")

    serialized = json.dumps(schema, sort_keys=True)

    for required_term in ("x_gcve", "vulnId", "recordType"):
        if required_term not in serialized:
            raise UpdateError(f"The selected GCVE schema does not contain {required_term!r}.")


def gcve_profile(existing: JsonObject, versions: Mapping[str, str]) -> JsonObject:
    version = versions["gcve"]
    profile_id = gcve_profile_id(version)
    profile = {
        **existing,
        "kind": "gcve",
        "label": existing.get("label", f"GCVE-BCP-05 {version}"),
        "bcp": "GCVE-BCP-05",
        "version": version,
        # A CVE record with the x_gcve extension.
        "baseProfile": cve_profile_id(versions["cve"]),
        "baseSchema": CVE.base_schema(versions["cve"]),
        "extensionSchemas": [GCVE.base_schema(version)],
        "semanticValidator": "gcve-bcp-05",
    }
    profile.pop("sourceMetadata", None)
    profile.setdefault(
        "schemaOverlay", {"path": f"overlays/{profile_id}.json", "applyTo": "rootOneOfBranches"}
    )
    profile.setdefault(
        "editor",
        {
            "layout": "editor/cve.layout.json",
            "layoutExtras": ["editor/gcve.layout-extra.json"],
            "variant": "Published",
            "augmenters": ["gcve-extensions"],
            "autoAdditionalPropertiesFrom": "containers.cna",
        },
    )
    profile.setdefault("validation", {"preferredRootBranch": {"keyword": "oneOf", "index": 0}})
    profile.setdefault("identifier", {"strategy": "gcve"})
    return profile


GCVE = SchemaSource(
    name="gcve",
    version_help="GCVE-BCP-05 version.",
    title="gcve-eu/bcp-validator",
    repository="https://github.com/gcve-eu/bcp-validator.git",
    default_ref="main",
    default_version="1.7",
    profile_id=gcve_profile_id,
    files=gcve_files,
    check=check_gcve_schema,
    profile=gcve_profile,
)


# --- OSV ----------------------------------------------------------------------


def osv_profile_id(version: str) -> str:
    return f"osv-{version}"


def osv_files(version: str) -> dict[Path, Path]:
    return {Path("validation/schema.json"): UPSTREAM / "osv" / version / "schema.json"}


def check_osv_schema(schema: JsonObject, version: str) -> None:
    properties = schema.get("properties")

    if (
        schema.get("title") != "Open Source Vulnerability"
        or not isinstance(properties, dict)
        or not {"id", "modified", "affected"} <= properties.keys()
    ):
        raise UpdateError("The selected file does not look like the OSV schema.")


def osv_profile(existing: JsonObject, versions: Mapping[str, str]) -> JsonObject:
    version = versions["osv"]
    # OSV is standalone; drop any stale baseProfile.
    existing.pop("baseProfile", None)
    # No editor.variant: the OSV schema has no root oneOf to pick from.
    # patch2vuln puts GCVE-BCP-05 x_gcve data into database_specific; the
    # overlay declares it there and the GCVE validator checks it.
    return {
        "editor": {"layout": "editor/osv.layout.json", "augmenters": ["gcve-extensions"]},
        "identifier": {"strategy": "osv"},
        "schemaOverlay": {"path": f"overlays/{osv_profile_id(version)}.json", "applyTo": "root"},
        "semanticValidator": "gcve-bcp-05",
        **existing,
        "kind": "osv",
        "label": existing.get("label", f"OSV {version}"),
        "version": version,
        "baseSchema": OSV.base_schema(version),
        "extensionSchemas": [GCVE.base_schema(versions["gcve"])],
    }


OSV = SchemaSource(
    name="osv",
    version_help="OSV schema version.",
    title="ossf/osv-schema",
    repository="https://github.com/ossf/osv-schema.git",
    default_ref="v1.9.2",
    default_version="1.9.2",
    profile_id=osv_profile_id,
    files=osv_files,
    check=check_osv_schema,
    profile=osv_profile,
)


# --- CSAF ---------------------------------------------------------------------

# Everything a CSAF document's schema needs, relative to the repository's
# csaf_<version>/ folder. Each file is vendored at the same relative path.
CSAF_SCHEMA_FILES = (
    "json_schema/csaf.json",
    "json_schema/meta.json",
    "json_schema/extension-content.json",
    "json_schema/extension-metadata.json",
    "json_schema/extension-metaschema.json",
    "referenced_schema/first/cvss-v2.0.json",
    "referenced_schema/first/cvss-v3.0.json",
    "referenced_schema/first/cvss-v3.1.json",
    "referenced_schema/first/cvss-v4.0.json",
    "referenced_schema/first/meta.json",
    "referenced_schema/certcc/DecisionPoint_2_0_0.schema.json",
    "referenced_schema/certcc/SelectionList_2_0_0.schema.json",
)


CSAF_MARKED_DEFINITIONS = [
    "branches_t",
    "product_id_t",
    "products_t",
    "product_group_id_t",
    "product_groups_t",
]


def csaf_profile_id(version: str) -> str:
    return f"csaf-{version}"


def csaf_files(version: str) -> dict[Path, Path]:
    return {
        Path(f"csaf_{version}") / relative: UPSTREAM / "csaf" / version / relative
        for relative in CSAF_SCHEMA_FILES
    }


def csaf_schema_resources(version: str) -> dict[str, str]:
    """The URLs the CSAF schema refers to, mapped to the vendored file that
    answers each. Explicit because FIRST's CVSS files don't state these URLs
    as their $id (2.0 and 3.0 have none, 3.1 and 4.0 add a date query)."""
    oasis = f"https://docs.oasis-open.org/csaf/csaf/v{version}/schema"
    first = "https://www.first.org/cvss"
    ssvc = "https://certcc.github.io/SSVC/data/schema/v2"

    return {
        f"{oasis}/meta.json": "json_schema/meta.json",
        f"{oasis}/extension-content.json": "json_schema/extension-content.json",
        f"{oasis}/extension-metadata.json": "json_schema/extension-metadata.json",
        f"{oasis}/extension-metaschema.json": "json_schema/extension-metaschema.json",
        f"{first}/cvss-v2.0.json": "referenced_schema/first/cvss-v2.0.json",
        f"{first}/cvss-v3.0.json": "referenced_schema/first/cvss-v3.0.json",
        f"{first}/cvss-v3.1.json": "referenced_schema/first/cvss-v3.1.json",
        f"{first}/cvss-v4.0.json": "referenced_schema/first/cvss-v4.0.json",
        f"{first}/meta.json": "referenced_schema/first/meta.json",
        f"{ssvc}/DecisionPoint_2_0_0.schema.json": (
            "referenced_schema/certcc/DecisionPoint_2_0_0.schema.json"
        ),
        f"{ssvc}/SelectionList_2_0_0.schema.json": (
            "referenced_schema/certcc/SelectionList_2_0_0.schema.json"
        ),
    }


def check_csaf_schema(schema: JsonObject, version: str) -> None:
    schema_id = schema.get("$id")
    document = as_dict(as_dict(schema.get("properties")).get("document"))
    declared = as_dict(as_dict(document.get("properties")).get("csaf_version")).get("const")

    if not isinstance(schema_id, str) or not schema_id.endswith(f"/v{version}/schema/csaf.json"):
        raise UpdateError(f"Unexpected CSAF schema identifier: {schema_id!r}")

    if declared != version:
        raise UpdateError(f"The selected CSAF schema is for version {declared!r}, not {version!r}.")


def csaf_profile(existing: JsonObject, versions: Mapping[str, str]) -> JsonObject:
    version = versions["csaf"]
    base = UPSTREAM / "csaf" / version
    # No editor.variant: the CSAF schema has no root oneOf to pick from.
    return {
        # 2020-12: the editor must check unevaluatedItems/dependentRequired too.
        "editor": {
            "layout": "editor/csaf.layout.json",
            "dialect": "2020-12",
            # The product tree and the product/group ID references get
            # their own editors; see frontend/src/editor/renderers/csaf/.
            "markDefinitions": CSAF_MARKED_DEFINITIONS,
        },
        "identifier": {"strategy": "csaf"},
        # CSAF's mandatory tests (spec 6.1), backend/.../csaf_mandatory/.
        "semanticValidator": "csaf-2.1",
        **existing,
        "kind": "csaf",
        "label": existing.get("label", f"CSAF {version}"),
        "version": version,
        "baseSchema": CSAF.base_schema(version),
        "schemaResources": {
            url: (base / path).as_posix() for url, path in csaf_schema_resources(version).items()
        },
    }


CSAF = SchemaSource(
    name="csaf",
    version_help="CSAF version (selects the repository's csaf_<version>/ folder).",
    title="oasis-tcs/csaf",
    repository="https://github.com/oasis-tcs/csaf.git",
    # CSAF 2.1 Committee Specification 01, release candidate 1: not an
    # OASIS Standard yet, so pinned to the exact tag.
    default_ref="csaf-2.1-cs-01-20261109-rc1",
    default_version="2.1",
    profile_id=csaf_profile_id,
    files=csaf_files,
    check=check_csaf_schema,
    profile=csaf_profile,
)


# In update order: GCVE needs the CVE version, OSV the GCVE one.
SOURCES: tuple[SchemaSource, ...] = (CVE, GCVE, OSV, CSAF)


def update_profiles(manifest: JsonObject, versions: Mapping[str, str]) -> None:
    """Write every source's profile and mark it as the format's current one."""
    profiles = manifest["profiles"]

    for source in SOURCES:
        profile_id = source.profile_id(versions[source.name])
        profiles[profile_id] = source.profile(_existing(profiles, profile_id), versions)
        manifest["currentProfiles"][source.name] = profile_id
