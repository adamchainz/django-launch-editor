from __future__ import annotations

import subprocess
import sys

import pytest

import django_launch_editor
from django_launch_editor.reporter import LaunchEditorExceptionReporter


def test_reporter_attribute():
    assert (
        django_launch_editor.LaunchEditorExceptionReporter
        is LaunchEditorExceptionReporter
    )


def test_unknown_attribute():
    with pytest.raises(AttributeError) as excinfo:
        django_launch_editor.nope  # noqa: B018

    assert str(excinfo.value) == "module 'django_launch_editor' has no attribute 'nope'"


def test_import_is_lazy():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, django_launch_editor; "
            + "print('django_launch_editor.reporter' in sys.modules)",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout == "False\n"
