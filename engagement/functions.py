import json

from django.conf import settings
from pypardot.client import PardotAPI

def get_pardot_client():
    return PardotAPI(
        sf_consumer_key=settings.PARDOT['sf_consumer_key'],
        sf_consumer_secret=settings.PARDOT['sf_consumer_secret'],
        sf_refresh_token=settings.PARDOT['sf_refresh_token'],
        business_unit_id=settings.PARDOT['business_unit_id'],
        version=settings.PARDOT['version']
    )

def get_prospect_lists(sf_id):
    p = get_pardot_client()

    prospect = p.prospects.read_by_fid(sf_id)

    public_lists = {}
    subscriptions = prospect['prospect']['lists']['list_subscription']
    for subscription in subscriptions:
        if subscription['list']['is_public']:
            public_lists['id'] = subscription['list']['id']
            public_lists['name'] = subscription['list']['name']

    # pprint.pprint(subscriptions)  # contains all the list information, even if it's not public
    return public_lists  # only returns the public list names - can be used to unsubscribe from lists
