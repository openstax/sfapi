from sf.models.adoption import Adoption
from sf.models.contact import Contact
from accounts.functions import get_logged_in_user_uuid
from .schemas import Message, AdoptionsSchema, ContactSchema

from ninja import NinjaAPI

api = NinjaAPI(
    version="0.0.1",
    title="OpenStax Salesforce API",
    description="Useful for pulling common data from Salesforce, focused on Instructors.",
)

possible_error_codes = frozenset([400, 401, 404])

@api.get("/contact", response={200: ContactSchema, possible_error_codes: Message}, tags=["user"])
def user(request):
    user_uuid = get_logged_in_user_uuid(request)

    if not user_uuid:
        return 401, {"message": "User is not authenticated."}

    try:
        contact = Contact.objects.get(accounts_uuid=user_uuid)
    except Contact.DoesNotExist:
        return 404, {"message": "User does not have a valid Salesforce Contact."}

    return contact

@api.get("/adoptions", response={200: AdoptionsSchema, possible_error_codes: Message}, tags=["user"])
def adoptions(request, confirmed: bool = None, assumed: bool = None):
    user_uuid = get_logged_in_user_uuid(request)
    if not user_uuid:
        return 401, {"message": "User is not authenticated."}

    contact = Contact.objects.get(accounts_uuid=user_uuid)
    if not contact:
        return 404, {"message": "User does not have a valid Salesforce Contact."}

    contact_adoptions = Adoption.objects.filter(contact=contact)
    if confirmed:
        contact_adoptions = contact_adoptions.filter(confirmation_type="OpenStax Confirmed Adoption")
    if assumed:
        contact_adoptions = contact_adoptions.exclude(confirmation_type="OpenStax Confirmed Adoption")

    if not contact_adoptions:
        return 404, {"message": "No adoptions found."}

    return {"count": len(contact_adoptions), "adoptions": contact_adoptions}
