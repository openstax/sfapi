"""
URL configuration for Camp Campaign.
Mounts the dashboard HTML views and wires the ninja API router.
"""

from django.urls import path

from . import html_views

app_name = "pardot"

urlpatterns = [
    path("", html_views.dashboard, name="dashboard"),
    path("admin-settings/", html_views.admin_settings, name="admin-settings"),
]
