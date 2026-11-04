from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.http import Http404, HttpRequest, HttpResponse
from django.http.response import HttpResponseBase
from django.urls import resolve

from django_launch_editor.reporter import add_launch_editor
from django_launch_editor.tokens import make_token

# Django’s debug 404 page names the view for the URL in this row.
RAISED_BY = '<th scope="row">Raised by:</th>'


class LaunchEditorMiddleware:
    """
    Make the “Raised by” view on Django’s debug 404 page into a link that
    opens it in the user’s editor.
    """

    sync_capable = True
    async_capable = True

    def __init__(
        self,
        get_response: (
            Callable[[HttpRequest], HttpResponseBase]
            | Callable[[HttpRequest], Awaitable[HttpResponseBase]]
        ),
    ) -> None:
        if not settings.DEBUG:
            raise MiddlewareNotUsed()

        self.get_response = get_response
        self.async_mode = iscoroutinefunction(self.get_response)

        if self.async_mode:
            # Mark the class as async-capable, but do the actual switch
            # inside __call__ to avoid swapping out dunder methods
            markcoroutinefunction(self)

    def __call__(
        self, request: HttpRequest
    ) -> HttpResponseBase | Awaitable[HttpResponseBase]:
        if self.async_mode:
            return self.__acall__(request)

        response = self.get_response(request)
        assert isinstance(response, HttpResponseBase)
        self.maybe_inject(request, response)
        return response

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        result = self.get_response(request)
        assert not isinstance(result, HttpResponseBase)  # type narrow
        response = await result
        self.maybe_inject(request, response)
        return response

    def maybe_inject(self, request: HttpRequest, response: HttpResponseBase) -> None:
        if (
            not settings.DEBUG
            or response.status_code != 404
            or not isinstance(response, HttpResponse)
            or response.headers.get("content-encoding", "")
            or response.headers.get("content-type", "").split(";", 1)[0] != "text/html"
        ):
            return

        content = response.content.decode(response.charset)
        if RAISED_BY not in content:
            return

        # Like Django’s get_caller(), resolve the URL if it was not resolved
        # before the 404, such as when middleware raised it.
        resolver_match = request.resolver_match
        if resolver_match is None:
            try:
                resolver_match = resolve(request.path_info)
            except Http404:
                return

        location = view_location(resolver_match.func)
        raised_by = make_token(*location) if location is not None else None
        response.content = add_launch_editor(
            content,  # type: ignore [arg-type]
            request,
            {"raisedBy": raised_by},
        )
        if "content-length" in response.headers:
            response["content-length"] = len(response.content)


def view_location(view: Any) -> tuple[str, int] | None:
    """
    Return the filename and line where the given view is defined, looking
    through decorators and to the class of class-based views.
    """
    view = inspect.unwrap(getattr(view, "view_class", view))
    try:
        filename = inspect.getsourcefile(view)
        if filename is None:
            return None
        _, line = inspect.getsourcelines(view)
    except (OSError, TypeError):
        return None
    return filename, line
