from typing import Any
from salesforce.functions import get_contact, get_adoptions

from ninja import NinjaAPI, Schema
from ninja.security import django_auth, HttpBearer

api = NinjaAPI()

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "supersecret":
            return token

class UserSchema(Schema):
    username: str
    is_authenticated: bool
    email: str = None
    first_name: str = None
    last_name: str = None

class Error(Schema):
    message: str

@api.get("/me", response=UserSchema, auth=django_auth)
def me(request):
    return request.user

@api.get("/bearer", response=UserSchema, auth=AuthBearer())
def bearer(request):
    return {"token": request.auth}

# @api.get("/contact/{uuid}")
# def contact_detail(request, uuid: str):
#     contact = get_contact(accounts_uuid=uuid)
#     if not contact:
#         return 404, {"message": "User not found."}
#     return contact

# @api.get("/contact/{contact_id}")
# def contact_detail(request, contact_id: str):
#     contact = get_contact(contact_id=contact_id)
#     if not contact:
#         return 404, {"message": "User not found."}
#     return contact


my_codes = frozenset({200, 400, 403, 404})


@api.get("/adoptions/{uuid}", response={my_codes: Any})
def adoptions(request, uuid: str):
    if not uuid:
        return 400, {"message": "Contact ID is required."}
    contact = get_contact(accounts_uuid=uuid)
    if not contact:
        return 404, {"message": "User does not have a valid Salesforce Contact."}
    contact_adoptions = get_adoptions(contact['Id'])
    if not contact_adoptions:
        return 404, {"message": "Adoptions not found."}
    return {"adoptions": contact_adoptions}


@api.get("/adoptions/{contact_id}/{adoption_id}")
def adoption_detail(request, adoption_id: int):
    # adoption = next((adoption for adoption in adoption_dict if adoption['id'] == id), None)

    return {"adoption": []}
