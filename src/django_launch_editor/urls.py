from __future__ import annotations

from django.conf import settings
from django.urls import URLPattern, path

app_name = "django_launch_editor"

urlpatterns: list[URLPattern] = []

# Only define the URL when DEBUG is on, to avoid importing the views module
# otherwise.
if settings.DEBUG:
    from django_launch_editor import views

    urlpatterns.append(path("launch/", views.launch, name="launch"))
