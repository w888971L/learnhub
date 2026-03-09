"""
URL configuration for LearnHub.

Routes:
    /admin/  — Django admin interface
    /        — All application URLs defined in core.urls
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]
