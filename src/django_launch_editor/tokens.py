from __future__ import annotations

import os

from django.core import signing

SALT = "django_launch_editor"

# Tokens are only valid for this long, to limit how long a leaked one can be
# used for.
MAX_AGE = 60 * 60 * 24  # seconds


def make_token(filename: str, line: int, column: int | None = None) -> str | None:
    """
    Return a signed token that allows opening the given file at the given
    line and column, or None if the file cannot be opened.
    """
    if not os.path.isfile(filename):
        return None
    return signing.dumps([filename, line, column], salt=SALT)


def load_token(token: str) -> tuple[str, int, int | None]:
    """
    Return the filename, line, and column from a token made by make_token().
    Raises django.core.signing.BadSignature if the token is invalid or has
    expired.
    """
    payload = signing.loads(token, salt=SALT, max_age=MAX_AGE)
    try:
        filename, line, column = payload
    except (TypeError, ValueError) as exc:
        # Such as a token from an older version, without a column.
        raise signing.BadSignature("Invalid token payload.") from exc
    return filename, line, column
