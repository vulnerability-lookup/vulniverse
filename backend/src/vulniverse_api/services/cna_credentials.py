from __future__ import annotations

from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

from ..extensions import db
from ..models import UserCnaCredential

# Every field required to configure a target. A row always has all of
# these — set_credential validates them together, there's no notion of a
# partially-configured target.
CREDENTIAL_FIELDS = (
    "cve_url",
    "short_name",
    "org_id",
    "cve_api_org",
    "cve_api_user",
    "cve_api_key",
)


class CredentialDecryptionError(RuntimeError):
    """Raised when a stored credential can't be decrypted — almost always
    because CNA_CREDENTIAL_ENCRYPTION_KEY changed since it was encrypted.
    """


def _fernet() -> Fernet:
    key = current_app.config["CNA_CREDENTIAL_ENCRYPTION_KEY"]

    return Fernet(key.encode() if isinstance(key, str) else key)


def get_credential(user_id: int, target: str) -> dict[str, str] | None:
    """Decrypted credential for this user/target, or None if unconfigured.
    Never exposed via any API response as-is — callers use this
    server-side only, e.g. to build outgoing request headers.
    """
    row = UserCnaCredential.query.filter_by(user_id=user_id, target=target).first()

    if row is None:
        return None

    try:
        api_key = _fernet().decrypt(row.cve_api_key_encrypted.encode()).decode()
    except InvalidToken as exc:
        raise CredentialDecryptionError(
            f"Stored CNA credential for target {target!r} could not be "
            "decrypted — CNA_CREDENTIAL_ENCRYPTION_KEY may have changed.",
        ) from exc

    return {
        "cve_url": row.cve_url,
        "short_name": row.short_name,
        "org_id": row.org_id,
        "cve_api_org": row.cve_api_org,
        "cve_api_user": row.cve_api_user,
        "cve_api_key": api_key,
    }


def is_credential_configured(user_id: int, target: str) -> bool:
    return (
        UserCnaCredential.query.filter_by(user_id=user_id, target=target).first()
        is not None
    )


def list_credentials(user_id: int) -> dict[str, dict[str, Any]]:
    """Non-secret fields for every target this user has configured, keyed
    by target — safe to return directly from an API response.
    """
    rows = UserCnaCredential.query.filter_by(user_id=user_id).all()

    return {
        row.target: {
            "cveUrl": row.cve_url,
            "shortName": row.short_name,
            "orgId": row.org_id,
            "cveApiOrg": row.cve_api_org,
            "cveApiUser": row.cve_api_user,
        }
        for row in rows
    }


def set_credential(
    user_id: int,
    target: str,
    fields: dict[str, Any],
) -> UserCnaCredential:
    """Create or update a target's credential. cve_api_key is required to
    create a new one, but optional when updating an existing row — an
    omitted/blank key on update leaves the previously-stored one in
    place, so the frontend never has to redisplay a secret to keep it.
    """
    row = UserCnaCredential.query.filter_by(user_id=user_id, target=target).first()

    required_fields = [key for key in CREDENTIAL_FIELDS if key != "cve_api_key"]
    missing = [key for key in required_fields if not fields.get(key)]

    if row is None and not fields.get("cve_api_key"):
        missing.append("cve_api_key")

    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")

    if row is None:
        row = UserCnaCredential(user_id=user_id, target=target)

    row.cve_url = fields["cve_url"]
    row.short_name = fields["short_name"]
    row.org_id = fields["org_id"]
    row.cve_api_org = fields["cve_api_org"]
    row.cve_api_user = fields["cve_api_user"]

    if fields.get("cve_api_key"):
        row.cve_api_key_encrypted = _fernet().encrypt(fields["cve_api_key"].encode()).decode()

    db.session.add(row)
    db.session.commit()

    return row


def delete_credential(user_id: int, target: str) -> bool:
    row = UserCnaCredential.query.filter_by(user_id=user_id, target=target).first()

    if row is None:
        return False

    db.session.delete(row)
    db.session.commit()

    return True
