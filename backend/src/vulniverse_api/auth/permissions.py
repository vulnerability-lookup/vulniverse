from collections.abc import Callable
from functools import wraps
from typing import Any

from flask_login import current_user, login_required

from .identity import is_local_mode


def admin_required[F: Callable[..., Any]](view: F) -> F:
    @wraps(view)
    @login_required
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if not current_user.is_admin:
            return {"message": "Admin access required."}, 403

        return view(*args, **kwargs)

    return wrapped  # type: ignore[return-value]


def multiuser_only[F: Callable[..., Any]](view: F) -> F:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if is_local_mode():
            return {
                "message": "Not available in local mode."
            }, 404

        return view(*args, **kwargs)

    return wrapped  # type: ignore[return-value]
