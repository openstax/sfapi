from django.contrib import admin
from django.urls import path
from api.api import api

def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
    path('sentry-debug/', trigger_error),
]
