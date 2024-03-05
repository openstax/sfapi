import datetime
from typing import List, Optional
from ninja import Field, Schema

# The schema for the response of endpoints are here
# The fields set here will be for validation (if creating), serialization, and /api/docs
# Schema returning multiple objects contain a parent Schema with the fields, and a child Schema with a count and objects
# Commented out fields might be useful, but can cause performance issues and are marked as suck

# General schema for errors returned by the API, change this if more details are needed with an error response
# See api_vX.py @api decorator response for usage
class ErrorSchema(Schema):
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
    active_book: Optional[bool]
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
    country: Optional[str] = Field(alias="billing_country")
    state: Optional[str] = Field(alias="billing_state")
    city: Optional[str] = Field(alias="billing_state")
    lms: Optional[str]
    sheer_id_school_name: Optional[str]

class AccountsSchema(Schema):
    count: int
    limit: int
    offset: int
    schools: List[AccountSchema]


############
# Contacts #
############
class ContactSchema(Schema):
    id: str
    first_name: str
    last_name: str
    full_name: str
    # school: AccountSchema = Field(alias="account") # might be a performance hit, but add if the details are needed
    school: str = Field(alias="account.name")
    role: Optional[str]
    position: Optional[str]
    adoption_status: Optional[str]
    subject_interest: Optional[str]
    lms: Optional[str]
    accounts_uuid: str
    verification_status: Optional[str]
    signup_date: Optional[datetime.datetime]
    lead_source: Optional[str]
    adoptions_json: Optional[str]

class ContactsSchema(Schema):
    count: int
    contacts: List[ContactSchema]

#############
# Adoptions #
#############
class AdoptionSchema(Schema):
    id: str
    # contact: ContactSchema # might be a performance hit, but add if the details are needed
    book: BookSchema = Field(alias="opportunity.book")
    base_year: Optional[int]
    school_year: Optional[str]
    school: str = Field(alias="opportunity.account.name")
    confirmation_type: Optional[str]
    students: Optional[int]
    how_using: Optional[str]
    confirmation_date: datetime.date

class AdoptionsSchema(Schema):
    count: int
    adoptions: List[AdoptionSchema]

###############
# Email Lists #
###############
class EmailListSchema(Schema):
    id: int
    name: str
