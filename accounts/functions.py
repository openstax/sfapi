from django.conf import settings
from .strategy_2 import Strategy2


def decrypt_cookie(cookie):
    strategy = Strategy2(
        signature_public_key=settings.SIGNATURE_PUBLIC_KEY,
        encryption_private_key=settings.ENCRYPTION_PRIVATE_KEY,
    )

    payload = strategy.decrypt(cookie)
    return payload

def get_logged_in_user_uuid(request):
    payload = decrypt_cookie(request.COOKIES.get(settings.SSO_COOKIE_NAME))
    if payload:
        return payload.user_uuid
    else:
        return None
