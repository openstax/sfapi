# This connection is not currently being used, but is here for future use - see django-salesforce and .models dir
from contextlib import ContextDecorator
from django.conf import settings

from django.contrib.sessions.backends.db import SessionStore
from simple_salesforce import Salesforce as SimpleSalesforce


class Salesforce(SimpleSalesforce, ContextDecorator):
    _default_session_key = 0

    def __init__(self, *args, **kwargs):
        session_store = SessionStore(session_key=self._default_session_key)
        if 'sf_instance' in session_store.keys() and 'sf_session_id' in session_store.keys():
            try:
                super(Salesforce, self).__init__(instance=session_store['sf_instance'],
                                                 session_id=session_store['sf_session_id'])
            except:
                raise RuntimeError("salesforce session failed")
        else:
            try:
                super(Salesforce, self).__init__(consumer_key=settings.SALESFORCE['consumer_key'],
                                                 consumer_secret=settings.SALESFORCE['consumer_secret'],
                                                 domain=settings.SALESFORCE['domain'])

            except AttributeError:
                super(Salesforce, self).__init__(*args, **kwargs)
            except TypeError:
                raise RuntimeError("salesforce init failed")
            session_store['sf_instance'] = self.sf_instance
            session_store['sf_session_id'] = self.session_id
            session_store.save()
            self.update_session_key(session_store.session_key)

    @classmethod
    def update_session_key(cls, key):
        cls._default_session_key = key

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if not exc == (None, None, None):
            session_store = SessionStore(session_key=self._default_session_key)
            session_store.delete()
            self.update_session_key(None)
        return False

