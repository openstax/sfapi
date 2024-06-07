import datetime
from typing import List, Optional
from ninja import Field, Schema, FilterSchema

# The schema for the response of endpoints are here
# The fields set here will be for validation (if creating), serialization, and /api/docs
# Schema returning multiple objects contain a parent Schema with the fields, and a child Schema with a count and objects
# Commented out fields might be useful, but can cause performance issues and are marked as suck

# General schema for errors returned by the API, change this if more details are needed with an error response
# See api_vX.py @api decorator response for usage
class ErrorSchema(Schema):
    code: int
    detail: str

########
# Books#
########
class BookSchema(Schema):
    id: str
    name: str = Field(description="The name of the book.")
    official_name: str
    type: Optional[str] = Field(description="The type of the book.")
    subject_areas: Optional[str]
    website_url: Optional[str]

class BooksSchema(Schema):
    count: int
    books: List[BookSchema]

############
# Accounts #
############
class AccountSchema(Schema):
    id: str
    name: str
    type: Optional[str]
    country: Optional[str]
    state: Optional[str]
    city: Optional[str]
    lms: Optional[str]
    sheer_id_school_name: Optional[str]

class AccountsSchema(Schema):
    count: int
    total_schools: int
    schools: List[AccountSchema]

class AccountFilterSchema(FilterSchema):
    name: Optional[str] = None
    type: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None


############
# Contacts #
############
class UserSchema(Schema):
    uuid: str

class ContactSchema(Schema):
    id: str
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: Optional[str]
    school: Optional[str]
    role: Optional[str]
    position: Optional[str]
    adoption_status: Optional[str]
    subject_interest: Optional[str]
    lms: Optional[str]
    accounts_uuid: str
    verification_status: Optional[str]
    signup_date: Optional[datetime.datetime]
    last_modified_date: Optional[datetime.datetime]
    lead_source: Optional[str]

class ContactsSchema(Schema):
    count: int
    contacts: List[ContactSchema]

#############
# Adoptions #
#############
class AdoptionSchema(Schema):
    id: str
    book: BookSchema
    base_year: Optional[int]
    school_year: Optional[str]
    school: str
    confirmation_type: Optional[str]
    students: Optional[int]
    savings: Optional[float]
    how_using: Optional[str]
    confirmation_date: Optional[datetime.date]

class AdoptionsSchema(Schema):
    count: int
    contact_id: str
    adoptions: List[AdoptionSchema]
    cache_create: Optional[datetime.datetime]
    cache_expire: Optional[datetime.datetime]

#########
# Cases #
#########

class CaseSchema(Schema):
    subject: str
    description: str
    product: Optional[str]
    feature: Optional[str]
    issue: Optional[str]
