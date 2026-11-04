from __future__ import annotations

import inspect
import json
import linecache
import re
import sys
from types import SimpleNamespace
from typing import Any
from unittest import mock

from django.conf import settings
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils.safestring import mark_safe
from django.views.debug import ExceptionReporter

import tests.urls_without_launch_editor
import tests.views
from django_launch_editor.reporter import (
    LaunchEditorExceptionReporter,
    frame_column,
    insert,
)
from django_launch_editor.tokens import load_token


def get_config(html: str) -> dict[str, Any]:
    match = re.search(
        r'<script id="django-launch-editor-data" type="application/json">(.*?)</script>',
        html,
    )
    assert match is not None
    return json.loads(match[1])  # type: ignore [no-any-return]


def make_reporter(**kwargs: Any) -> LaunchEditorExceptionReporter:
    request = kwargs.pop("request", RequestFactory().get("/"))
    try:
        exec("raise ValueError('Oh no')")
    except ValueError:
        exc_type, exc_value, tb = sys.exc_info()
    return LaunchEditorExceptionReporter(request, exc_type, exc_value, tb, **kwargs)


@override_settings(DEBUG=True)
class LaunchEditorExceptionReporterTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.client = self.client_class(raise_request_exception=False)

    def test_error_page(self):
        response = self.client.get("/error/")

        assert response.status_code == 500
        html = response.text
        assert html.index('id="django-launch-editor-data"') < html.index("</body>")
        assert "<script>(function () {" in html
        config = get_config(html)
        assert config["url"] == "/__launch_editor__/launch/"
        assert config["template"] is None
        assert len(config["frames"]) >= 2
        filename, line, column = load_token(config["frames"][-1])
        assert filename == tests.views.__file__
        assert line == inspect.getsourcelines(tests.views.error)[1] + 1
        assert column == 5

    def test_template_error(self):
        response = self.client.get("/template-error/")

        assert response.status_code == 500
        config = get_config(response.text)
        filename, line, column = load_token(config["template"])
        assert filename == str(settings.BASE_DIR / "templates" / "error.html")
        assert line == 2
        assert column is None

    def test_column_non_ascii(self):
        response = self.client.get("/column-error/")

        assert response.status_code == 500
        config = get_config(response.text)
        filename, line, column = load_token(config["frames"][-1])
        assert filename == tests.views.__file__
        source_line = linecache.getline(filename, line)
        # Counted in characters, not the UTF-8 bytes that Python reports.
        assert column == source_line.index('prices["€"]') + 1

    def test_frame_without_file(self):
        reporter = make_reporter()

        config = get_config(reporter.get_traceback_html())

        # The frame for exec()’d code has no file.
        assert config["frames"][-1] is None
        assert config["frames"][0] is not None

    def test_no_traceback(self):
        reporter = LaunchEditorExceptionReporter(
            RequestFactory().get("/"), None, None, None
        )

        config = get_config(reporter.get_traceback_html())

        assert config["frames"] == []

    @override_settings(DEBUG=False)
    def test_not_debug(self):
        html = make_reporter().get_traceback_html()

        assert "django-launch-editor" not in html
        assert "</body>" in html

    def test_email(self):
        html = make_reporter(is_email=True).get_traceback_html()

        assert "django-launch-editor" not in html

    def test_no_request(self):
        html = make_reporter(request=None).get_traceback_html()

        assert "django-launch-editor" not in html

    @override_settings(ROOT_URLCONF="tests.urls_without_launch_editor")
    def test_url_not_installed(self):
        response = self.client.get("/error/")

        assert response.status_code == 500
        html = response.text
        assert 'id="django-launch-editor-data"' not in html
        banner = html.index('<div id="django-launch-editor-banner" role="note">')
        assert html.index("</header>") < banner < html.index('<div id="traceback">')
        assert (
            '<code>path("__launch_editor__/", '
            + 'include("django_launch_editor.urls"))</code>'
        ) in html
        assert "<code>tests.urls_without_launch_editor</code>" in html

    @override_settings(ROOT_URLCONF="tests.urls_without_launch_editor")
    def test_url_not_installed_request_urlconf(self):
        reporter = make_reporter()
        reporter.request.urlconf = tests.urls_without_launch_editor  # type: ignore [union-attr]

        html = reporter.get_traceback_html()

        assert "<code>tests.urls_without_launch_editor</code>" in html

    def test_data_not_used(self):
        # In case a future Django version stops calling get_traceback_data()
        # from get_traceback_html().
        with mock.patch.object(
            ExceptionReporter, "get_traceback_html", return_value="<p>Hi</p>"
        ):
            html = make_reporter().get_traceback_html()

        assert html == "<p>Hi</p>"

    def test_data_not_used_after_text(self):
        reporter = make_reporter()
        reporter.get_traceback_text()

        with mock.patch.object(
            ExceptionReporter, "get_traceback_html", return_value="<p>Hi</p>"
        ):
            html = reporter.get_traceback_html()

        # Not decorated with stale data from get_traceback_text().
        assert html == "<p>Hi</p>"

    def test_data_not_kept(self):
        reporter = make_reporter()

        reporter.get_traceback_html()

        assert not hasattr(reporter, "_launch_editor_data")

    def test_text(self):
        reporter = make_reporter()

        text = reporter.get_traceback_text()

        assert "ValueError" in text
        assert "django-launch-editor" not in text

    def test_no_body_end(self):
        class NoBodyReporter(LaunchEditorExceptionReporter):
            @property
            def html_template_path(self):
                return settings.BASE_DIR / "templates" / "no_body.html"

        reporter = NoBodyReporter(RequestFactory().get("/"), None, None, None)

        html = reporter.get_traceback_html()

        assert "django-launch-editor" not in html


# The `raise` line in tests.views.error, indented by four spaces.
LINE = inspect.getsourcelines(tests.views.error)[1] + 1


def fake_frame(
    positions: list[tuple[int | None, ...]], filename: str = tests.views.__file__
) -> dict[str, Any]:
    code = SimpleNamespace(co_positions=lambda: iter(positions))
    tb = SimpleNamespace(tb_frame=SimpleNamespace(f_code=code), tb_lasti=0)
    return {"tb": tb, "filename": filename, "lineno": LINE}


class FrameColumnTests(SimpleTestCase):
    def test_column(self):
        assert frame_column(fake_frame([(LINE, LINE, 4, 10)])) == 5

    def test_other_line(self):
        assert frame_column(fake_frame([(LINE - 1, LINE, 4, 10)])) is None

    def test_no_column(self):
        assert frame_column(fake_frame([(LINE, LINE, None, None)])) is None

    def test_no_positions(self):
        assert frame_column(fake_frame([])) is None

    def test_unreadable_line(self):
        frame = fake_frame([(LINE, LINE, 4, 10)], filename="/does/not/exist.py")
        assert frame_column(frame) is None


class InsertTests(SimpleTestCase):
    def test_before_last(self):
        assert (
            insert(mark_safe("a</b>c</b>"), "</b>", "X", before=True) == "a</b>cX</b>"
        )

    def test_after_first(self):
        assert (
            insert(mark_safe("a</b>c</b>"), "</b>", "X", before=False) == "a</b>Xc</b>"
        )

    def test_before_missing(self):
        assert insert(mark_safe("abc"), "</b>", "X", before=True) == "abc"

    def test_after_missing(self):
        assert insert(mark_safe("abc"), "</b>", "X", before=False) == "abc"
