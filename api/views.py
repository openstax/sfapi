from typing import Any
import json
import datetime
import pytz
from django.core import serializers

from openstax_salesforce.models import Adoption, Contact, Account, Book
from accounts.functions import get_logged_in_user_uuid

from ninja import NinjaAPI

api = NinjaAPI()

@api.get("/contact", response={frozenset({200, 401, 404}): Any})
def user(request):
    user_uuid = get_logged_in_user_uuid(request)
    if not user_uuid:
        return 401, {"message": "User is not authenticated."}

    try:
        contact = Contact.objects.get(accounts_uuid=user_uuid)
    except Contact.DoesNotExist:
        return 404, {"message": "User does not have a valid Salesforce Contact."}
    return {"contact": json.loads(serializers.serialize('json', [contact]))}

@api.get("/adoptions", response={frozenset({200, 400, 401, 404}): Any})
def adoptions(request, confirmed: bool = False, assumed: bool = False):
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

    return {"adoptions": json.loads(serializers.serialize('json', contact_adoptions))}

# TODO: not working
@api.get("/contacts/{days}", response={frozenset({200, 400, 404}): Any})
def contacts(request, days: int):
    if not days:
        return 400, {"message": "Period is required."}
    start = datetime.datetime.now(pytz.UTC)
    end = datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=days)
    contacts = Contact.objects.filter(last_activity_date__gte=start, last_activity_date__lte=end)
    if not contacts:
        return 404, {"message": f'No contacts updated in the last {days} days.'}
    return {"contacts": contacts}
