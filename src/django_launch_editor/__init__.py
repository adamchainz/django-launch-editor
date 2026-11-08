from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django_launch_editor.reporter import LaunchEditorExceptionReporter

__all__ = ["LaunchEditorExceptionReporter"]


def __getattr__(name: str) -> Any:
    # Lazily import the reporter, to avoid its import cost when the library
    # is installed but not in use, such as when DEBUG is off.
    if name == "LaunchEditorExceptionReporter":
        from django_launch_editor.reporter import LaunchEditorExceptionReporter

        return LaunchEditorExceptionReporter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
