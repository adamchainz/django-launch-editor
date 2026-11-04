from __future__ import annotations

import re

from django.test import SimpleTestCase, override_settings

from tests.test_reporter import get_config


@override_settings(DEBUG=True)
class DjangoMarkupTests(SimpleTestCase):
    """
    Check the parts of Django’s debug pages that launch-editor.js relies on,
    so changes in new Django versions are noticed.
    """

    def setUp(self):
        super().setUp()
        self.client = self.client_class(raise_request_exception=False)

    def test_traceback_frames(self):
        html = self.client.get("/error/").text

        frames = get_config(html)["frames"]
        traceback = html[html.index('<div id="browserTraceback">') :]
        # Frames are matched to tokens by position.
        assert traceback.count('<li class="frame ') == len(frames)
        locations = re.findall(
            r'<li class="frame [^"]*">\s*<code class="fname">[^<]+</code>, line \d+,',
            traceback,
        )
        assert len(locations) == len(frames)

    def test_exception_location(self):
        html = self.client.get("/error/").text

        summary = html[html.index('<header id="summary">') : html.index("</header>")]
        assert re.search(
            r'<th scope="row">Exception Location:</th>\s*'
            + r'<td><span class="fname">[^<]+</span>, line \d+,',
            summary,
        )

    def test_template_error(self):
        html = self.client.get("/template-error/").text

        assert re.search(
            r'<div id="template">\s*<h2>[^<]*</h2>\s*'
            + r"<p>In template <code>[^<]+</code>, error at line <strong>\d+</strong>",
            html,
        )

    def test_not_found_raised_by(self):
        html = self.client.get("/not-found/").text

        summary = html[html.index('<header id="summary">') : html.index("</header>")]
        assert re.search(
            r'<th scope="row">Raised by:</th>\s*<td>tests\.views\.not_found</td>',
            summary,
        )
