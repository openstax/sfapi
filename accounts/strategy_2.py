import jwe
import jwt
from sentry_sdk import capture_exception

class Strategy2:
    def __init__(self, signature_public_key, encryption_private_key):
        self.signature_public_key = signature_public_key
        self.signature_algorithm = 'RS256'
        self.encryption_algorithm = 'dir'
        self.encryption_method = 'A256GCM'
        self.encryption_private_key = encryption_private_key

    def decrypt(self, cookie):
        if not cookie:
            return None

        try:
            decrypted_payload = jwe.decrypt(cookie.encode(), self.encryption_private_key.encode())

            decoded_payload = jwt.decode(
                decrypted_payload,
                self.signature_public_key,
                audience="OpenStax",
                algorithms=[self.signature_algorithm]
            )

            return Payload(decoded_payload)
        except Exception as e:
            capture_exception(e)
            return None

class Payload:
    def __init__(self, payload_dict):
        self.payload_dict = payload_dict
        self.user_uuid = payload_dict['sub']['uuid']
        self.user_id = payload_dict['sub']['id']
        self.name = payload_dict['sub']['name']
