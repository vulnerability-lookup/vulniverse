"""Patch2Vuln batches: several commits analysed at once, then reviewed
one by one in the editor (a candidate becomes a record when saved).

A batch belongs to the current organisation, like its records.
Patch2Vuln only knows the jobs; which batch they belong to, and what
became of each, is kept here.
"""

from __future__ import annotations

from typing import Any

from flask import request
from flask_login import current_user

from ..auth.organisations import current_organisation
from ..extensions import db
from ..models import Patch2VulnBatch, Patch2VulnCandidate
from ..services.patch2vuln import (
    cancel_job,
    get_job_result,
    get_job_status,
    get_patch2vuln_config,
    submit_bulk_jobs,
)
from ..services.profiles import known_profiles
from . import api_bp, require_panel
from .patch2vuln import normalize_commit_url

type ApiResponse = tuple[dict[str, Any], int]

# Patch2Vuln's own queue holds 100 jobs by default, for every client.
MAX_BATCH_SIZE = 50
OPEN_STATUSES = {"queued", "running"}


def disabled_error() -> ApiResponse | None:
    if not get_patch2vuln_config().enabled:
        return {"message": "Patch2Vuln is disabled"}, 403
    return None


def find_batch(batch_id: int) -> Patch2VulnBatch | None:
    """The batch, if it belongs to the current organisation."""
    organisation = current_organisation()
    batch = db.session.get(Patch2VulnBatch, batch_id)

    if (
        batch is None
        or organisation is None
        or batch.organisation_id != organisation.id
    ):
        return None
    return batch


def find_candidate(candidate_id: int) -> Patch2VulnCandidate | None:
    candidate = db.session.get(Patch2VulnCandidate, candidate_id)

    if candidate is None or find_batch(candidate.batch_id) is None:
        return None
    return candidate


def candidate_title(candidate: Patch2VulnCandidate) -> str | None:
    result = candidate.result or {}
    cna = ((result.get("record") or {}).get("containers") or {}).get("cna") or {}
    title = cna.get("title") or (result.get("osv") or {}).get("summary")
    return title if isinstance(title, str) else None


def candidate_response(candidate: Patch2VulnCandidate) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "commitUrl": candidate.commit_url,
        "status": candidate.status,
        "title": candidate_title(candidate),
        "dismissed": candidate.dismissed,
        "recordId": candidate.record_id,
    }


def batch_summary(batch: Patch2VulnBatch) -> dict[str, Any]:
    statuses = [candidate.status for candidate in batch.candidates]
    return {
        "id": batch.id,
        "name": batch.name,
        "profile": batch.profile,
        "createdAt": batch.created_at.isoformat(),
        "createdBy": batch.created_by.email if batch.created_by else None,
        "total": len(statuses),
        "open": sum(status in OPEN_STATUSES for status in statuses),
        "completed": statuses.count("completed"),
        "reviewed": sum(
            candidate.record_id is not None or candidate.dismissed
            for candidate in batch.candidates
        ),
    }


def refresh(batch: Patch2VulnBatch) -> str | None:
    """Ask Patch2Vuln about the batch's unfinished jobs and keep the
    results of finished ones. Returns an error message when Patch2Vuln
    can't be reached; the last known statuses stay as they were."""
    for candidate in batch.candidates:
        if candidate.status not in OPEN_STATUSES:
            continue

        try:
            status = get_job_status(candidate.job_id)["status"]
            if status == "completed":
                candidate.result = get_job_result(candidate.job_id)
        except LookupError:
            # Patch2Vuln has forgotten the job (its results expire).
            status = "expired"
        except TypeError:
            # Succeeded, but the result isn't a usable record.
            status = "failed"
        except RuntimeError as exc:
            # Unreachable: don't wait for a timeout per remaining job.
            db.session.commit()
            return str(exc)

        candidate.status = status

    db.session.commit()
    return None


@api_bp.get("/patch2vuln/batches")
@require_panel("patch2vuln")
def list_patch2vuln_batches() -> ApiResponse:
    organisation = current_organisation()
    if organisation is None:
        return {"batches": []}, 200

    batches = (
        Patch2VulnBatch.query.filter_by(organisation_id=organisation.id)
        .order_by(Patch2VulnBatch.created_at.desc(), Patch2VulnBatch.id.desc())
        .all()
    )
    return {"batches": [batch_summary(batch) for batch in batches]}, 200


@api_bp.post("/patch2vuln/batches")
@require_panel("patch2vuln")
def create_patch2vuln_batch() -> ApiResponse:
    error = disabled_error()
    if error is not None:
        return error

    organisation = current_organisation()
    if organisation is None:
        return {"message": "You are not a member of any organisation yet."}, 403

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    name = payload.get("name")
    profile = payload.get("profile")
    commit_urls = payload.get("commitUrls")

    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 128:
        return {"message": "A name of up to 128 characters is required."}, 400
    if not isinstance(profile, str) or profile not in known_profiles():
        return {"message": f"Unknown profile: {profile!r}"}, 400
    if not isinstance(commit_urls, list) or not all(
        isinstance(url, str) for url in commit_urls
    ):
        return {"message": "commitUrls must be an array of strings."}, 400

    try:
        sources = [normalize_commit_url(url) for url in commit_urls if url.strip()]
    except ValueError as exc:
        return {"message": str(exc)}, 400

    # The same commit twice would only be analysed twice.
    sources = list(dict.fromkeys(sources))

    if not sources:
        return {"message": "At least one commit URL is required."}, 400
    if len(sources) > MAX_BATCH_SIZE:
        return {"message": f"A batch can have at most {MAX_BATCH_SIZE} commits."}, 400

    try:
        jobs = submit_bulk_jobs(sources)
    except ValueError as exc:
        return {"message": str(exc)}, 400
    except RuntimeError as exc:
        return {"message": str(exc)}, 502

    batch = Patch2VulnBatch(
        organisation_id=organisation.id,
        created_by_id=current_user.id,
        name=name.strip(),
        profile=profile,
        candidates=[
            Patch2VulnCandidate(
                position=position,
                commit_url=source,
                job_id=job["jobId"],
                status=job["status"],
                dismissed=False,
            )
            for position, (source, job) in enumerate(zip(sources, jobs, strict=True))
        ],
    )
    db.session.add(batch)
    db.session.commit()

    return batch_summary(batch), 201


@api_bp.get("/patch2vuln/batches/<int:batch_id>")
@require_panel("patch2vuln")
def get_patch2vuln_batch(batch_id: int) -> ApiResponse:
    batch = find_batch(batch_id)
    if batch is None:
        return {"message": "Batch not found."}, 404

    refresh_error = refresh(batch) if get_patch2vuln_config().enabled else None

    return {
        **batch_summary(batch),
        "candidates": [candidate_response(candidate) for candidate in batch.candidates],
        "refreshError": refresh_error,
    }, 200


@api_bp.delete("/patch2vuln/batches/<int:batch_id>")
@require_panel("patch2vuln")
def delete_patch2vuln_batch(batch_id: int) -> ApiResponse:
    batch = find_batch(batch_id)
    if batch is None:
        return {"message": "Batch not found."}, 404

    for candidate in batch.candidates:
        if candidate.status in OPEN_STATUSES:
            try:
                cancel_job(candidate.job_id)
            except LookupError:
                pass
            except RuntimeError as exc:
                # Deleting now would leave the jobs running unseen.
                return {"message": f"Could not cancel the open analyses: {exc}"}, 502

    db.session.delete(batch)
    db.session.commit()
    return {"id": batch_id}, 200


@api_bp.get("/patch2vuln/candidates/<int:candidate_id>")
@require_panel("patch2vuln")
def get_patch2vuln_candidate(candidate_id: int) -> ApiResponse:
    candidate = find_candidate(candidate_id)
    if candidate is None:
        return {"message": "Candidate not found."}, 404
    if candidate.result is None:
        return {"message": "This analysis has no result."}, 409

    return {
        **candidate_response(candidate),
        "batchId": candidate.batch_id,
        "profile": candidate.batch.profile,
        "result": candidate.result,
    }, 200


@api_bp.post("/patch2vuln/candidates/<int:candidate_id>/dismiss")
@require_panel("patch2vuln")
def dismiss_patch2vuln_candidate(candidate_id: int) -> ApiResponse:
    candidate = find_candidate(candidate_id)
    if candidate is None:
        return {"message": "Candidate not found."}, 404

    payload = request.get_json(silent=True)
    dismissed = payload.get("dismissed", True) if isinstance(payload, dict) else True
    if not isinstance(dismissed, bool):
        return {"message": "dismissed must be a boolean."}, 400

    candidate.dismissed = dismissed
    db.session.commit()
    return candidate_response(candidate), 200
