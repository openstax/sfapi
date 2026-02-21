import factory
from django.utils import timezone

from db.models import Account, Adoption, Book, Contact, Opportunity


class AccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Account

    id = factory.Sequence(lambda n: f'001000000000{n:03d}')
    name = factory.Faker('company')
    type = 'College/University (4)'
    city = factory.Faker('city')
    state = factory.Faker('state')
    country = 'US'
    country_code = 'US'
    created_date = factory.LazyFunction(timezone.now)
    last_modified_date = factory.LazyFunction(timezone.now)


class BookFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Book

    id = factory.Sequence(lambda n: f'a0B000000000{n:03d}')
    name = factory.Sequence(lambda n: f'Book {n}')
    official_name = factory.Sequence(lambda n: f'Official Book Name {n}')
    type = 'Textbook'
    active_book = True


class ContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contact

    id = factory.Sequence(lambda n: f'003000000000{n:03d}')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    full_name = factory.LazyAttribute(lambda o: f'{o.first_name} {o.last_name}')
    email = factory.Faker('email')
    verification_status = 'confirmed'
    accounts_uuid = factory.Faker('uuid4')
    account = factory.SubFactory(AccountFactory)
    signup_date = factory.LazyFunction(timezone.now)
    last_modified_date = factory.LazyFunction(timezone.now)


class OpportunityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Opportunity

    id = factory.Sequence(lambda n: f'006000000000{n:03d}')
    account = factory.SubFactory(AccountFactory)
    name = factory.Sequence(lambda n: f'Opportunity {n}')
    stage_name = 'Confirmed Adoption Won'
    close_date = factory.LazyFunction(lambda: timezone.now().date())
    owner_id = '005000000000001'
    created_date = factory.LazyFunction(timezone.now)
    created_by_id = '005000000000001'
    last_modified_date = factory.LazyFunction(timezone.now)
    last_modified_by_id = '005000000000001'
    system_modstamp = factory.LazyFunction(timezone.now)
    contact = factory.SubFactory(ContactFactory)
    book = factory.SubFactory(BookFactory)


class AdoptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Adoption

    id = factory.Sequence(lambda n: f'a0A000000000{n:03d}')
    contact = factory.SubFactory(ContactFactory)
    adoption_number = factory.Sequence(lambda n: f'ADO-{n:06d}')
    created_date = factory.LazyFunction(timezone.now)
    last_modified_date = factory.LazyFunction(timezone.now)
    system_modstamp = factory.LazyFunction(timezone.now)
    opportunity = factory.SubFactory(OpportunityFactory)
    base_year = 2024
    adoption_type = 'Faculty/Teacher Adoption'
    school_year = '2024-2025'
    confirmation_type = 'OpenStax Confirmed Adoption'
    students = 50
    savings = 5000.00
