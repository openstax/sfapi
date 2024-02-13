from django.conf import settings
from .strategy_2 import Strategy2


def decrypt_cookie(cookie):
    strategy = Strategy2(
        signature_public_key=settings.SIGNATURE_PUBLIC_KEY,
        signature_algorithm='RS256',
        encryption_private_key=settings.ENCRYPTION_PRIVATE_KEY,
        encryption_method='A256GCM',
        encryption_algorithm='dir'
    )

    payload = strategy.decrypt(cookie)
    return payload

def get_logged_in_user_uuid(request):
    """
    This simplifies getting the logged in user id - since this happens often.
    Requires SSO_COOKIE_NAME to be set in settings file.
    Takes an optional bypass_cookie_check param to bypass cookie checking for local dev / testing
    which returns -1 (a never valid user id)
    :param request:
    :return: user_uuid from SSO cookie
    """
    decrypted_cookie = decrypt_cookie(request.COOKIES.get(settings.SSO_COOKIE_NAME))
    if decrypted_cookie:
        return decrypted_cookie.user_uuid
    else:
        return None
