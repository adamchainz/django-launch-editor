from __future__ import annotations

import itertools
import linecache
from pathlib import Path
from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html, json_script
from django.utils.safestring import SafeString, mark_safe
from django.views.debug import ExceptionReporter

from django_launch_editor.tokens import make_token

SCRIPT = (Path(__file__).parent / "launch-editor.js").read_text(encoding="utf-8")

STYLE = """
button.django-launch-editor {
  background: none; border: none; padding: 0; margin: 0;
  font: inherit; color: inherit; text-align: inherit;
  text-decoration: underline; cursor: pointer;
  &:hover { text-decoration-thickness: 2px; }
  & .fname { user-select: text; }
  &:disabled { cursor: progress; }
}
.django-launch-editor-status {
  color: #666;
  &.error { color: #c00; }
}
dialog.django-launch-editor-dialog {
  margin: auto; max-width: 40em; padding: 1.5em;
  border: 1px solid #ccc; border-radius: 6px;
  &::backdrop { background: rgba(0, 0, 0, 0.4); }
  & h2 { margin: 0 0 0.5em; }
  & p { margin: 0 0 0.5em; }
  & code {
    display: flow-root; padding: 0.5em; background: #f0f0f0;
    overflow-wrap: anywhere; user-select: all;
    &[hidden] { display: none; }
  }
  & .django-launch-editor-copy {
    float: left; margin: 0 0.5em 0 0; padding: 0.4em;
    line-height: 0; cursor: pointer;
  }
  & form {
    clear: both; margin-top: 1em; text-align: right;
    & button { padding: 0.4em 1.2em; font: inherit; cursor: pointer; }
  }
}
"""

BANNER_STYLE = """
#django-launch-editor-banner { padding: 10px 20px; background: #fec; border-bottom: 1px solid #ccc; }
#django-launch-editor-banner code { font-size: 100%; }
"""


class LaunchEditorExceptionReporter(ExceptionReporter):
    """
    Exception reporter that makes file locations on the debug error page into
    links that open them in the user’s editor.
    """

    def get_traceback_data(self) -> dict[str, Any]:
        data = super().get_traceback_data()
        # Keep the data for get_traceback_html(), rather than computing it
        # twice.
        self._launch_editor_data: dict[str, Any] = data
        return data

    def get_traceback_html(self) -> SafeString:
        html = super().get_traceback_html()
        return self.add_launch_editor(html, self._launch_editor_data)

    def add_launch_editor(self, html: SafeString, data: dict[str, Any]) -> SafeString:
        # Never add links to error emails, or when DEBUG is off, since the
        # view will not work then.
        if not settings.DEBUG or self.is_email or self.request is None:
            return html

        frames = [
            make_token(frame["filename"], frame["lineno"], frame_column(frame))
            if frame["tb"] is not None
            else None
            for frame in data["frames"]
        ]

        template_info = data["template_info"]
        if template_info:
            template = make_token(template_info["name"], template_info["line"])
        else:
            template = None

        return add_launch_editor(
            html, self.request, {"frames": frames, "template": template}
        )


def frame_column(frame: dict[str, Any]) -> int | None:
    """
    Return the 1-based column where the frame’s current expression starts, if
    it’s on the frame’s line.
    """
    tb = frame["tb"]
    start_line, _, start_column, _ = next(
        itertools.islice(tb.tb_frame.f_code.co_positions(), tb.tb_lasti // 2, None),
        (None, None, None, None),
    )
    if start_line != frame["lineno"] or start_column is None:
        return None

    # Positions are UTF-8 byte offsets, but editors count characters.
    source_line = linecache.getline(frame["filename"], frame["lineno"])
    if not source_line:
        return None
    prefix = source_line.encode()[:start_column]
    return len(prefix.decode(errors="replace")) + 1


def add_launch_editor(
    html: SafeString, request: HttpRequest, config: dict[str, Any]
) -> SafeString:
    """
    Add the script that makes file locations into links to a debug page, or a
    banner explaining how to install the URLs if they’re missing.
    """
    try:
        url = reverse("django_launch_editor:launch")
    except NoReverseMatch:
        return insert(html, "</header>", banner_html(request), before=False)

    config = {"url": url, "frames": [], "template": None, **config}
    return insert(
        html,
        "</body>",
        f"<style>{STYLE}</style>"
        + json_script(config, "django-launch-editor-data")
        + f"<script>{SCRIPT}</script>",
        before=True,
    )


def banner_html(request: HttpRequest) -> str:
    urlconf = getattr(request, "urlconf", None) or settings.ROOT_URLCONF
    if not isinstance(urlconf, str):
        urlconf = urlconf.__name__
    return format_html(
        "<style>{}</style>"
        + '<div id="django-launch-editor-banner" role="note">'
        + "<strong>django-launch-editor</strong> cannot make file locations "
        + "into links, because its URLs are not installed. Add "
        + '<code>path("__launch_editor__/", '
        + 'include("django_launch_editor.urls"))</code> '
        + "to <code>urlpatterns</code> in <code>{}</code>."
        + "</div>",
        mark_safe(BANNER_STYLE),
        urlconf,
    )


def insert(html: SafeString, marker: str, extra: str, *, before: bool) -> SafeString:
    """
    Insert extra HTML before the last occurrence of marker, or after the first
    one, or return the HTML unchanged if marker is not found.
    """
    if before:
        head, found, tail = html.rpartition(marker)
        if found:
            return mark_safe(head + extra + found + tail)
    else:
        head, found, tail = html.partition(marker)
        if found:
            return mark_safe(head + found + extra + tail)
    return html
