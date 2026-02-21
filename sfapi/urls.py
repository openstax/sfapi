from django.contrib import admin
from django.urls import path

from api.api_v1 import api
from sf.views import info

urlpatterns = [
    path('admin/', admin.site.urls),
    path('info/', info),
    path('api/v1/', api.urls),
]
