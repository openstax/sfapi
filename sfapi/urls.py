from django.contrib import admin
from django.urls import path
from api.api_v1 import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', api.urls),
]
