from django.contrib import admin
from django.urls import path
from api.api_v1 import api

def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', api.urls),
    path('sentry-debug/', trigger_error),
]
