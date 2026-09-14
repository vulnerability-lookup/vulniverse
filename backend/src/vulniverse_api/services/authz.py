from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask_login import current_user, login_required


def admin_required[F: Callable[..., Any]](view: F) -> F:
    """Like flask_login's login_required, but also requires
    current_user.is_admin. The blueprint-wide login gate
    (api/__init__.py) already covers "logged in at all" for every
    route; this is the extra check for admin-only ones.
    """

    @wraps(view)
    @login_required
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if not current_user.is_admin:
            return {"message": "Admin access required."}, 403

        return view(*args, **kwargs)

    return wrapped  # type: ignore[return-value]
