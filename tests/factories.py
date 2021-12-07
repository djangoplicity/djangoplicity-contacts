from djangoplicity.contacts.models import Label, Contact, Country, Region, Field, GroupCategory, ContactGroup
from djangoplicity.contacts.labels import LABEL_PAPER_CHOICES
from django.core.management import call_command
from io import StringIO
from faker.factory import Factory
from datetime import datetime
import pytz
from django.conf import settings


utc = pytz.timezone('UCT')
fake = Factory.create()

LABEL_PAPER = [k for k, v in LABEL_PAPER_CHOICES]


def create_datetime(year, month, day, hour, minute, second, microsecond):
    return datetime(year, month, day,  hour, minute, second, microsecond, utc)


def call_update_regions_command(*args, **kwargs):
    out = StringIO()
    call_command(
        "update_regions",
        *args,
        stdout=out,
        stderr=StringIO(),
        **kwargs
    )
    return out.getvalue()


def contacts_count():
    return Contact.objects.count()


def factory_label(data):
    default = {
        "name": fake.company(),
        "paper": fake.random_element(LABEL_PAPER),
        "repeat": fake.random_element(range(1, 9)),
        "style": fake.texts(),
        "template": fake.texts(),
        "enabled": fake.boolean(),
    }

    if data is not None:
        default.update(data)
    return Label(**default)


def factory_field(data):
    default = {
        "slug": fake.slug(),
        "name": fake.word(),
        "blank": fake.boolean(),
    }

    if data is not None:
        default.update(data)
    return Field(**data)


def factory_contact(data):
    country = fake.random_element(Country.objects.all())
    region = fake.random_element(Region.objects.filter(country_id=country.id))

    default = {
        "title": fake.prefix(),
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "position": fake.job(),
        "organisation": fake.company(),
        "department": fake.company_suffix(),
        "street_1": fake.address(),
        "street_2": fake.address(),
        "zip": fake.zipcode(),
        "city": fake.city(),
        "country": country,
        "region": region,
        "tax_code": fake.zipcode(),
        "phone": fake.phone_number(),
        "website": fake.url(),
        "social": fake.url(),
        "email": fake.email(),
        "language": settings.LANGUAGE_CODE,
        "group_order": None,
    }

    if data is not None:
        default.update(data)

    return Contact(**default)


def factory_contact_group(data):
    default = {
        'name': fake.word(),
        'category': fake.random_element(GroupCategory.objects.all()),
        'order': fake.random_digit_not_null()
    }
    if data is not None:
        default.update(data)
    return ContactGroup(**default)
