from vulniverse_api.services.cvss_consistency import cvss_warnings

V31 = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"  # 10.0 CRITICAL


def record(cvss: dict, adp: bool = False) -> dict:
    container = {"metrics": [{"format": "CVSS", "cvssV3_1": cvss}]}
    return {
        "containers": {
            "cna": {} if adp else container,
            **({"adp": [container]} if adp else {}),
        }
    }


def test_consistent_object_has_no_warnings():
    assert (
        cvss_warnings(
            record(
                {
                    "version": "3.1",
                    "vectorString": V31,
                    "baseScore": 10.0,
                    "baseSeverity": "CRITICAL",
                    "attackVector": "NETWORK",
                    "scope": "CHANGED",
                }
            )
        )
        == []
    )


def test_score_severity_and_metric_fields_that_disagree_are_flagged():
    warnings = cvss_warnings(
        record(
            {
                "version": "3.1",
                "vectorString": V31,
                "baseScore": 9.8,
                "baseSeverity": "HIGH",
                "attackVector": "LOCAL",
                "scope": "CHANGED",
            },
            adp=True,
        )
    )

    assert [w["path"][-1] for w in warnings] == [
        "baseScore",
        "baseSeverity",
        "attackVector",
    ]
    assert warnings[0]["path"][:4] == ["containers", "adp", 0, "metrics"]
    assert all(w["severity"] == "warning" for w in warnings)
    assert "scores 10.0" in warnings[0]["message"]


def test_cvss4_and_cvss2_and_unparsable_vectors():
    v4 = {
        "version": "4.0",
        "vectorString": "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N",
        "baseScore": 9.3,
        "baseSeverity": "CRITICAL",
        "userInteraction": "ACTIVE",
    }
    v2 = {
        "version": "2.0",
        "vectorString": "AV:N/AC:L/Au:N/C:C/I:C/A:C",
        "baseScore": 7.5,
    }
    entry = {
        "containers": {
            "cna": {
                "metrics": [
                    {"cvssV4_0": v4},
                    {"cvssV2_0": v2},
                    {"cvssV3_1": {"vectorString": "garbage", "baseScore": 1}},
                ]
            }
        }
    }

    assert [(w["path"][3], w["path"][-1]) for w in cvss_warnings(entry)] == [
        (0, "userInteraction"),
        (1, "baseScore"),
    ]


def test_records_without_containers_are_ignored():
    assert cvss_warnings({"id": "OSV-1"}) == []
