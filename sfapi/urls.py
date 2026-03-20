from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

from api.api_v1 import api

urlpatterns = [
    path("ping/", lambda request: HttpResponse()),
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls),
    path("pardot/", include("pardot.urls")),
]
