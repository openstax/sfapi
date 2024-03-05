from functools import partial

from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse

from ninja.openapi.views import openapi_json, openapi_view

from openstax_accounts.functions import get_logged_in_user_id, get_user_info


class OpenAPIOpenStaxAuthenticationMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if isinstance(view_func, partial):
            view = view_func.func
            if view in [openapi_view, openapi_json]:
                api = view_func.keywords['api']
                user_id = get_logged_in_user_id(request)
                user_info = get_user_info(user_id)
                if user_info:
                    print(user_info)
                    is_admin = user_info['is_administrator']
                    if is_admin:
                        return view(request, api)
                return JsonResponse({"detail": "You are not authorized to access this page."}, status=401)
