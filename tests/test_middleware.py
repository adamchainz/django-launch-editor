from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from http import HTTPStatus
from typing import Any
from unittest import mock

import pytest
from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpResponse, HttpResponseNotFound
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import ResolverMatch

import tests.views
from django_launch_editor.middleware import LaunchEditorMiddleware, view_location
from django_launch_editor.tokens import load_token
from tests.test_reporter import get_config


def view_line(view: object) -> int:
    return inspect.getsourcelines(view)[1]  # type: ignore [arg-type]


@override_settings(DEBUG=True)
class LaunchEditorMiddlewareTests(SimpleTestCase):
    @override_settings(DEBUG=False)
    def test_not_debug(self):
        with pytest.raises(MiddlewareNotUsed):
            LaunchEditorMiddleware(lambda request: HttpResponse())

    def test_not_found(self):
        response = self.client.get("/not-found/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        config = get_config(response.text)
        assert config["url"] == "/__launch_editor__/launch/"
        assert config["frames"] == []
        filename, line, column = load_token(config["raisedBy"])
        assert filename == tests.views.__file__
        # The decorator line, after unwrapping the decorator.
        assert line == view_line(inspect.unwrap(tests.views.not_found))
        assert column is None

    def test_not_found_class(self):
        response = self.client.get("/not-found-class/")

        config = get_config(response.text)
        filename, line, _ = load_token(config["raisedBy"])
        assert filename == tests.views.__file__
        assert line == view_line(tests.views.NotFoundView)

    async def test_not_found_async(self):
        response = await self.async_client.get("/not-found/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        config = get_config(response.content.decode())
        filename, _, _ = load_token(config["raisedBy"])
        assert filename == tests.views.__file__

    def test_unmatched_url(self):
        response = self.client.get("/does-not-exist/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert "django-launch-editor" not in response.text

    @override_settings(ROOT_URLCONF="tests.urls_without_launch_editor")
    def test_url_not_installed(self):
        response = self.client.get("/not-found/")

        assert response.status_code == HTTPStatus.NOT_FOUND
        html = response.text
        assert 'id="django-launch-editor-data"' not in html
        banner = html.index('<div id="django-launch-editor-banner" role="note">')
        assert html.index("</header>") < banner < html.index('<main id="info">')

    def run_middleware(self, response: HttpResponse) -> HttpResponse:
        request = RequestFactory().get("/not-found/")
        request.resolver_match = mock_resolver_match()
        middleware = LaunchEditorMiddleware(lambda request: response)
        result = middleware(request)
        assert isinstance(result, HttpResponse)
        return result

    def test_not_resolved_before_404(self):
        # Such as when middleware raises Http404 before URL resolution.
        content = '<th scope="row">Raised by:</th></header></body>'
        request = RequestFactory().get("/not-found/")
        assert request.resolver_match is None
        middleware = LaunchEditorMiddleware(
            lambda request: HttpResponseNotFound(content)
        )

        response = middleware(request)

        assert isinstance(response, HttpResponse)
        filename, _, _ = load_token(get_config(response.text)["raisedBy"])
        assert filename == tests.views.__file__

    def test_not_resolvable(self):
        content = '<th scope="row">Raised by:</th></header></body>'
        request = RequestFactory().get("/does-not-exist/")
        middleware = LaunchEditorMiddleware(
            lambda request: HttpResponseNotFound(content)
        )

        response = middleware(request)

        assert isinstance(response, HttpResponse)
        assert response.text == content

    def test_content_length(self):
        content = '<th scope="row">Raised by:</th></header></body>'
        not_found = HttpResponseNotFound(content)
        not_found["content-length"] = len(content)

        response = self.run_middleware(not_found)

        assert "django-launch-editor-data" in response.text
        assert response["content-length"] == str(len(response.content))

    def test_other_status(self):
        content = '<th scope="row">Raised by:</th></header></body>'
        response = self.run_middleware(HttpResponse(content))

        assert response.text == content

    def test_not_html(self):
        content = '<th scope="row">Raised by:</th></header></body>'
        response = self.run_middleware(
            HttpResponseNotFound(content, content_type="text/plain")
        )

        assert response.text == content

    def test_encoded(self):
        content = '<th scope="row">Raised by:</th></header></body>'
        not_found = HttpResponseNotFound(content)
        not_found["content-encoding"] = "gzip"

        response = self.run_middleware(not_found)

        assert response.content == content.encode()

    def test_not_debug_page(self):
        content = "<header></header><p>Custom 404</p></body>"
        response = self.run_middleware(HttpResponseNotFound(content))

        assert response.text == content

    def test_view_without_source(self):
        content = '<th scope="row">Raised by:</th></header></body>'
        request = RequestFactory().get("/not-found/")
        request.resolver_match = mock_resolver_match(func=len)
        middleware = LaunchEditorMiddleware(
            lambda request: HttpResponseNotFound(content)
        )

        response = middleware(request)

        assert isinstance(response, HttpResponse)
        assert get_config(response.text)["raisedBy"] is None


def mock_resolver_match(
    func: Callable[..., Any] = tests.views.not_found,
) -> ResolverMatch:
    return ResolverMatch(func, (), {})


class ViewLocationTests(SimpleTestCase):
    def test_function(self):
        assert view_location(tests.views.error) == (
            tests.views.__file__,
            view_line(tests.views.error),
        )

    def test_partial(self):
        assert view_location(functools.partial(tests.views.error)) is None

    def test_builtin(self):
        assert view_location(len) is None

    def test_no_source_file(self):
        namespace: dict[str, object] = {}
        exec("def view(request): pass", namespace)

        assert view_location(namespace["view"]) is None

    def test_source_file_unknown(self):
        with mock.patch("inspect.getsourcefile", return_value=None):
            assert view_location(tests.views.error) is None
