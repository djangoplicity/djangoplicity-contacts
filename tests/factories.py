from djangoplicity.contacts.models import Label, Contact, Country, Region, Field, GroupCategory, ContactGroup, \
    ImportSelector, DEDUPLICATION_STATUS, Deduplication
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


def factory_import_selector(template, data):
    """
    Create a Import SelectorDefines a selector for an import template.
    This allows the template to only import certain rows (e.g. if a
    specific column contains an x in a cell it will be imported).
    """
    default = {
        'template': template,
        'header': fake.random_element([u'Website', 'Phone', 'Email', 'Language', 'Region/State',
                                       'Country', 'Zipcode', 'City', 'Street 2', 'Street 1', 'Groups',
                                       'Department', 'Organization', 'Position', 'First name', 'Last name',
                                       'Title']),
        'value': fake.word(),
        'case_sensitive': fake.boolean(),
    }

    if data is not None:
        default.update(data)

    return ImportSelector(**default)


def factory_request_data(rows=None, limit = None):
    data = {'_import': 'Import'}
    if rows is None:
        data.update({
            '_selected_import_2': 'on',
            '_selected_merge_contact_2': 'new',
            '2_new-title': 'Mrs.',
            '2_new-first_name': 'Jhon',
            '2_new-last_name': 'Doe',
            '2_new-position': 'Product designer',
            '2_new-organisation': 'Johnson, Smith and Mclean',
            '2_new-department': 'LLC',
            '2_new-street_1': '36310 Juan FordsNew Sabrina, NY 54546',
            '2_new-street_2': '35304 Carlson BranchMeyertown, NJ 71989',
            '2_new-zip': '15418',
            '2_new-city': 'Lauratown',
            '2_new-country': '7',
            '2_new-region': '544',
            '2_new-tax_code': '',
            '2_new-phone': '890.067.9460',
            '2_new-website': 'https://www.smith.org/',
            '2_new-social': '',
            '2_new-email': 'jhondoe@cox-ayala.com',
            '2_new-language': 'en',
            '2_new-groups': ['1', '2'],
            '2_new-group_order': None,
        })
    else:
        for idx, row in enumerate(rows):
            r_number = idx + 2
            data.update({
                '_selected_import_' + str(r_number): 'on',
                '_selected_merge_contact_' + str(r_number): 'new',
                str(r_number) + '_new-title': row['title'],
                str(r_number) + '_new-first_name': row['first_name'],
                str(r_number) + '_new-last_name': row['last_name'],
                str(r_number) + '_new-position': row['position'],
                str(r_number) + '_new-organisation': row['organisation'],
                str(r_number) + '_new-department': row['department'],
                str(r_number) + '_new-street_1': row['street_1'],
                str(r_number) + '_new-street_2': row['street_2'],
                str(r_number) + '_new-zip': row['zip'],
                str(r_number) + '_new-city': row['city'],
                str(r_number) + '_new-country': row['country'],
                str(r_number) + '_new-region': row['region'],
                str(r_number) + '_new-tax_code': '',
                str(r_number) + '_new-phone': row['phone'],
                str(r_number) + '_new-website': row['website'],
                str(r_number) + '_new-social': '',
                str(r_number) + '_new-email': row['email'],
                str(r_number) + '_new-language': row['language'],
                str(r_number) + '_new-groups': row['groups'],
            })
            if limit and idx > limit:
                break
    return data


def factory_invalid_data(rows=None):
    data = {'_import': 'Import'}
    if rows is None:
        data.update({
            '_selected_import_2': 'on',
            '_selected_merge_contact_2': 'new',
            '2_new-title': 'Mrs.',
            '2_new-first_name': 'Jhon',
            '2_new-last_name': 'Doe',
            '2_new-position': 'Product designer',
            '2_new-organisation': 'Johnson, Smith and Mclean',
            '2_new-department': 'LLC',
            '2_new-street_1': '36310 Juan FordsNew Sabrina, NY 54546',
            '2_new-street_2': '35304 Carlson BranchMeyertown, NJ 71989',
            '2_new-zip': '15418',
            '2_new-city': 'Lauratown',
            '2_new-country': '-invalid-',  # invalid country
            '2_new-region': '-invalid region-',  # invalid region
            '2_new-tax_code': '',
            '2_new-phone': '890.067.9460',
            '2_new-website': 'https://www.smith.org/',
            '2_new-social': '',
            '2_new-email': 'jhondoe@cox-ayala.com',
            '2_new-language': 'en',
            '2_new-groups': ['1', '2'],
            '2_new-group_order': None,
        })
        return data


def factory_deduplication(data):
    default = {
        'status': DEDUPLICATION_STATUS[0][0],
        'last_deduplication': None,
        'duplicate_contacts': '',
        'deduplicated_contacts': '',
        'max_display': 25,
        'min_score_display': 0.7
    }

    if data is not None:
        default.update(data)
    return Deduplication(**default)


def factory_deduplication_form(data, action):
    default = {
        '_deduplication': 'Deduplication'
    }
    for key, value in data:
        contact = Contact.objects.get(id=key)
        for key2, values in value.items():
            default.update({
                'action_contact_' + key + '_' + key2: action,
                key + '_' + key2 + '-title': 'updated',
                key + '_' + key2 + '-first_name': contact.first_name,
                key + '_' + key2 + '-last_name': contact.last_name,
                key + '_' + key2 + '-position': contact.position,
                key + '_' + key2 + '-organisation': contact.organisation,
                key + '_' + key2 + '-department': contact.department,
                key + '_' + key2 + '-street_1': contact.street_1,
                key + '_' + key2 + '-street_2': contact.street_2,
                key + '_' + key2 + '-zip': contact.zip,
                key + '_' + key2 + '-city': contact.city,
                key + '_' + key2 + '-country': contact.country,
                key + '_' + key2 + '-region': contact.region,
                key + '_' + key2 + '-tax_code': contact.tax_code,
                key + '_' + key2 + '-phone': contact.phone,
                key + '_' + key2 + '-website': contact.website,
                key + '_' + key2 + '-social': contact.social,
                key + '_' + key2 + '-email': contact.email,
                key + '_' + key2 + '-language': contact.language,
                key + '_' + key2 + '-groups': contact.groups,
                key + '_' + key2 + '-group_order': contact.group_order,
            })
    return default
