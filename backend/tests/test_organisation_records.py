"""Records belong to organisations: colleagues share drafts, outsiders
don't see them, IDs are unique per organisation, and new records go to
the current organisation. One live request per test (see insert_record
in test_records_api.py for why)."""

from __future__ import annotations

from conftest import logged_in_client, make_user
from flask import Flask
from sqlalchemy import text
from test_records_api import create_draft, insert_record, minimal_cve_record

from vulniverse_api.api.records import commit_or_conflict
from vulniverse_api.auth.local_user import create_local_user
from vulniverse_api.extensions import db
from vulniverse_api.models import Membership, Organisation, VulnerabilityRecord


def test_colleagues_see_each_others_drafts_in_the_list(
    app, test_user, colleague_client
) -> None:
    insert_record(app, "CVE-2026-01001", test_user.id, is_draft=True)

    response = colleague_client.get("/api/v1/records")

    assert [r["identifier"] for r in response.get_json()["records"]] == [
        "CVE-2026-01001"
    ]
    assert response.get_json()["records"][0]["organisation"]["name"] == "Acme"


def test_colleagues_can_open_and_change_each_others_drafts(
    app, test_user, colleague_client
) -> None:
    rid = insert_record(app, "CVE-2026-01002", test_user.id, is_draft=True)

    response = colleague_client.put(
        f"/api/v1/records/{rid}",
        json={"record": minimal_cve_record("CVE-2026-01002"), "isDraft": True},
    )

    assert response.status_code == 200
    assert response.get_json()["version"] == 2


def test_outsiders_cannot_change_a_published_record(
    app, test_user, other_client
) -> None:
    rid = insert_record(app, "CVE-2026-01003", test_user.id, is_draft=False)

    response = other_client.put(
        f"/api/v1/records/{rid}",
        json={"record": minimal_cve_record("CVE-2026-01003"), "isDraft": False},
    )

    assert response.status_code == 403


def test_the_same_id_may_exist_in_two_organisations(
    app, test_user, other_client
) -> None:
    insert_record(app, "CVE-2026-01004", test_user.id, is_draft=True)

    # Nor does the answer reveal the other organisation's private draft.
    assert create_draft(other_client, "CVE-2026-01004").status_code == 201


def test_ids_stay_unique_within_an_organisation(
    app, test_user, colleague_client
) -> None:
    insert_record(app, "CVE-2026-01005", test_user.id, is_draft=True)

    assert create_draft(colleague_client, "cve-2026-01005").status_code == 409


def test_a_new_record_goes_to_the_current_organisation(client, organisation) -> None:
    response = create_draft(client, "CVE-2026-01006")

    assert response.status_code == 201
    assert response.get_json()["organisation"] == {
        "id": organisation.id,
        "name": "Acme",
    }
    assert response.get_json()["version"] == 1


def test_the_session_chooses_among_several_organisations(
    app, organisation, other_organisation
) -> None:
    user = make_user(app, "both@example.com", organisation)
    with app.app_context():
        db.session.add(
            Membership(
                user_id=user.id, organisation_id=other_organisation.id, role="editor"
            )
        )
        db.session.commit()

    both_client = logged_in_client(app, user)
    with both_client.session_transaction() as session:
        session["organisation_id"] = other_organisation.id

    assert (
        create_draft(both_client, "CVE-2026-01007").get_json()["organisation"]["name"]
        == "Other"
    )


def test_a_user_without_organisation_sees_nothing_and_cannot_create(app) -> None:
    lonely_client = logged_in_client(app, make_user(app, "lonely@example.com", None))

    response = create_draft(lonely_client, "CVE-2026-01008")

    assert response.status_code == 403
    assert "not a member of any organisation" in response.get_json()["message"]


def test_a_user_without_organisation_has_an_empty_list(app, test_user) -> None:
    insert_record(app, "CVE-2026-01009", test_user.id, is_draft=False)
    lonely_client = logged_in_client(app, make_user(app, "lonely@example.com", None))

    assert lonely_client.get("/api/v1/records").get_json()["records"] == []


def test_instance_admins_can_filter_the_list_by_organisation(
    app, test_user, other_user, admin_client, other_organisation
) -> None:
    insert_record(app, "CVE-2026-01010", test_user.id, is_draft=True)
    insert_record(app, "CVE-2026-01011", other_user.id, is_draft=True)

    response = admin_client.get(f"/api/v1/records?organisation={other_organisation.id}")

    assert [r["identifier"] for r in response.get_json()["records"]] == [
        "CVE-2026-01011"
    ]


def test_local_mode_gets_its_own_organisation_once(app: Flask) -> None:
    with app.app_context():
        user = create_local_user()
        create_local_user()  # Again, as at every start.

        memberships = Membership.query.filter_by(user_id=user.id).all()
        assert [(m.organisation.name, m.role) for m in memberships] == [
            ("Local workspace", "admin")
        ]
        assert Organisation.query.count() == 1


def test_local_mode_keeps_a_migrated_default_organisation(
    app: Flask, organisation
) -> None:
    with app.app_context():
        user = create_local_user()
        # As after the migration: the local user already in an organisation.
        Membership.query.filter_by(user_id=user.id).delete()
        db.session.add(
            Membership(user_id=user.id, organisation_id=organisation.id, role="editor")
        )
        db.session.commit()

        create_local_user()

        assert [
            m.organisation_id for m in Membership.query.filter_by(user_id=user.id)
        ] == [organisation.id]
        assert VulnerabilityRecord.query.count() == 0


# --- Saves based on an outdated copy ---------------------------------------


def save(client, rid: int, cve_id: str, **extra):
    return client.put(
        f"/api/v1/records/{rid}",
        json={"record": minimal_cve_record(cve_id), "isDraft": True, **extra},
    )


def test_a_save_based_on_the_current_version_goes_through(
    app, test_user, client
) -> None:
    rid = insert_record(app, "CVE-2026-03001", test_user.id, is_draft=True)

    response = save(client, rid, "CVE-2026-03001", version=1)

    assert response.status_code == 200
    assert response.get_json()["version"] == 2


def test_a_save_based_on_an_outdated_version_is_refused(app, test_user, client) -> None:
    rid = insert_record(app, "CVE-2026-03002", test_user.id, is_draft=True)
    with app.app_context():
        db.session.get(VulnerabilityRecord, rid).version = 3  # type: ignore[union-attr]
        db.session.commit()

    response = save(client, rid, "CVE-2026-03002", version=2)

    assert response.status_code == 409
    assert "Someone else saved this record" in response.get_json()["message"]
    with app.app_context():
        assert db.session.get(VulnerabilityRecord, rid).version == 3  # type: ignore[union-attr]


def test_a_save_without_a_version_still_goes_through(app, test_user, client) -> None:
    rid = insert_record(app, "CVE-2026-03003", test_user.id, is_draft=True)

    assert save(client, rid, "CVE-2026-03003").status_code == 200


def test_the_version_must_be_an_integer(app, test_user, client) -> None:
    rid = insert_record(app, "CVE-2026-03004", test_user.id, is_draft=True)

    assert save(client, rid, "CVE-2026-03004", version="1").status_code == 400


def test_of_two_simultaneous_saves_the_second_fails(app, test_user) -> None:
    rid = insert_record(app, "CVE-2026-03005", test_user.id, is_draft=True)

    with app.app_context():
        # This save loaded version 1 and passed the version check…
        record = db.session.get(VulnerabilityRecord, rid)
        assert record is not None
        # …while another one committed in between, behind its back.
        db.session.execute(
            text("UPDATE vulnerability_record SET version = 2 WHERE id = :id"),
            {"id": rid},
        )
        record.is_draft = False
        record.version += 1

        response = commit_or_conflict()

        assert response is not None
        assert response[1] == 409
        # Rolled back: not published. (The simulated other save was in the
        # same transaction here, so it's rolled back too.)
        assert db.session.get(VulnerabilityRecord, rid).is_draft is True  # type: ignore[union-attr]
