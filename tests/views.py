from __future__ import annotations

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View
from django.views.decorators.http import require_GET


def error(request: HttpRequest) -> HttpResponse:
    raise ValueError("Oh no")


def template_error(request: HttpRequest) -> HttpResponse:
    return render(request, "error.html")


def column_error(request: HttpRequest) -> HttpResponse:
    prices = {"£": 1}
    return HttpResponse("£" + str(prices["€"]))


@require_GET
def not_found(request: HttpRequest) -> HttpResponse:
    raise Http404("Nope")


class NotFoundView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        raise Http404("Nope")
