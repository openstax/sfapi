from django.contrib import admin
from django.urls import path, include
from api.views import api

def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path('admin/', admin.site.urls),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('api/', api.urls),
    path('sentry-debug/', trigger_error),
]
