from __future__ import annotations

import importlib
import sys

from django.test import SimpleTestCase, override_settings
from django.urls import URLPattern

import django_launch_editor.urls


class UrlsTests(SimpleTestCase):
    def reload_urls(self, *, debug: bool) -> list[URLPattern]:
        with override_settings(DEBUG=debug):
            module = importlib.reload(django_launch_editor.urls)
        # Restore the module to its normal state for other tests.
        self.addCleanup(self.restore_urls)
        return list(module.urlpatterns)

    def restore_urls(self) -> None:
        with override_settings(DEBUG=True):
            importlib.reload(django_launch_editor.urls)

    def test_debug(self):
        urlpatterns = self.reload_urls(debug=True)

        assert [p.name for p in urlpatterns] == ["launch"]

    def test_not_debug(self):
        views = sys.modules.pop("django_launch_editor.views")
        try:
            urlpatterns = self.reload_urls(debug=False)
            views_imported = "django_launch_editor.views" in sys.modules
        finally:
            sys.modules["django_launch_editor.views"] = views

        assert urlpatterns == []
        assert not views_imported
