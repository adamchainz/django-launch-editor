from __future__ import annotations

from django.urls import path

from tests import views

urlpatterns = [
    path("error/", views.error),
    path("not-found/", views.not_found),
]
