# coding=utf-8
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from djangoplicity.contacts.models import Label, LabelRender, Contact, Field, GroupCategory, CountryGroup, PostalZone, \
    Country, Region, ContactGroup, ContactGroupAction, ImportTemplate
from .factories import factory_label, factory_contact, \
    contacts_count, factory_field, factory_contact_group
from djangoplicity.contacts.importer import CSVImporter, ExcelImporter

try:
    from mock import patch, MagicMock
except ImportError:
    from unittest.mock import patch, MagicMock


class TestImportTemplate(TestCase):
    """
    Test template defines how a CSV or Excel file should be imported into the contacts model.
    It supports mapping columns to contacts fields.
    """
    fixtures = ['actions', 'initial']

    def setUp(self):
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@newsletters.org',
            password='password123'
        )
        self.client.force_login(self.admin_user)

    def test_template_get_data_from_csv_file(self):
        """
        Test open csv import file
        """
        filepath = './tests/contacts.csv'
        template = ImportTemplate.objects.get(name='TEST Contacts all')
        importer = template.get_importer('./tests/contacts.csv')

        self.assertIsInstance(importer, CSVImporter)
        self.assertIsNotNone(importer)

        self.assertEqual(len(importer), 99)
        self.assertEqual(len(importer.cols), 17)
        self.assertEqual(str(template), 'TEST Contacts all')

        row_0_email = importer.row(0)['Email']
        row_1_email = importer.row(1)['Email']
        row_2_email = importer.row(2)['Email']
        row_3_email = importer.row(3)['Email']
        row_4_email = importer.row(4)['Email']

        self.assertEqual(row_0_email, 'adam70@yahoo.com')
        self.assertEqual(row_1_email, 'pgrant@green-shaw.biz')
        self.assertEqual(row_2_email, 'bradley00@lopez.com')
        self.assertEqual(row_3_email, 'joneskristen@hotmail.com')
        self.assertEqual(row_4_email, 'greenryan@hernandez.com')

    def test_template_get_data_from_xls_file(self):
        """
        Test open xls import file
        """
        filepath = './tests/contacts.xls'
        template = ImportTemplate.objects.get(name='TEST Contacts all')
        template.clear_selector_cache()
        # clear caches
        template.clear_mapping_cache()
        importer = template.get_importer(filepath)

        self.assertIsInstance(importer, ExcelImporter)
        self.assertIsNotNone(importer)

        self.assertEqual(len(importer), 100)
        self.assertEqual(len(importer.cols), 17)
        self.assertEqual(len(importer.header()), 17)
        self.assertEqual(str(template), 'TEST Contacts all')

        # Get specific row
        row = importer.row(0)
        self.assertEqual(row, {
            'City': 'Lauratown',
            'Country': 'Germany',
            'Department': 'LLC',
            'Email': 'michael11@cox-ayala.com',
            'First name': 'Christopher',
            'Groups': 'Public NL, Public NL-invite, Unknown Group',
            'Language': 'en',
            'Last name': 'Wade',
            'Organization': 'Johnson, Smith and Mclean',
            'Phone': '890.067.9460',
            'Position': 'Product designer',
            'Region/State': 'Schleswig-Holstein',
            'Street 1': '36310 Juan Fords\nNew Sabrina, NY 54546',
            'Street 2': '35304 Carlson Branch\nMeyertown, NJ 71989',
            'Title': 'Mrs.',
            'Website': 'https://www.smith.org/',
            'Zipcode': 15418.0
        })
        # test import data
        data = template.extract_data(filepath)
        first_row = data.next()
        second_row = data.next()

        self.assertEqual(type(first_row), dict)
        self.assertEqual(second_row, {
            'city': u'Francisburgh',
            'country': 7,
            'department': u'Ltd',
            'email': u'tracy77@hotmail.com',
            'first_name': u'Angela',
            'groups': [1, 2],
            'language': u'en',
            'last_name': u'Spencer',
            'organisation': u'Alexander, Rivera and Jones',
            'phone': u'752.462.1748x89014',
            'position': u'Accommodation manager',
            'region': 550,
            'street_1': u'005 Huber Crest\nPort Marychester, NJ 69633',
            'street_2': u'31342 Katrina Village\nWest Cathybury, WA 38502',
            'title': u'Mrs.',
            'website': u'http://www.carter-king.com/',
            'zip': 78583
        })

        # Test preview table
        mappings_rows, data_table = template.preview_data(filepath)

        # test table header
        self.assertEqual(len(data_table), 100)
        self.assertEqual(len(mappings_rows), 18)

        # test the first table row
        self.assertEqual(type(data_table[0]), list)
        self.assertEqual(len(data_table[0]), 18)
