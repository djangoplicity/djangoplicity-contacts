# coding=utf-8
from django.db import models
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from djangoplicity.contacts.models import Label, LabelRender, Contact, Field, GroupCategory, CountryGroup, PostalZone, \
    Country, Region, ContactGroup, ContactGroupAction, ImportTemplate, ImportMapping, ImportSelector, ImportGroupMapping
from .factories import factory_label, factory_contact, \
    contacts_count, factory_field, factory_contact_group, factory_import_selector
from djangoplicity.contacts.importer import CSVImporter, ExcelImporter

try:
    from mock import patch, MagicMock
except ImportError:
    from unittest.mock import patch, MagicMock


class BasicTestCase(TestCase):
    fixtures = ['actions', 'initial']

    def setUp(self):
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@newsletters.org',
            password='password123'
        )
        self.client.force_login(self.admin_user)


class TestImportTemplate(BasicTestCase):
    """
    Test template defines how a CSV or Excel file should be imported into the contacts model.
    It supports mapping columns to contacts fields.
    """

    def test_template_get_data_from_csv_file(self):
        """
        Test open csv import file
        """
        filepath = './tests/contacts.csv'
        template = ImportTemplate.objects.get(name='TEST Contacts all')
        importer = template.get_importer('./tests/contacts.csv')

        self.assertIsInstance(importer, CSVImporter)
        self.assertIsNotNone(importer)

        self.assertEqual(len(importer), 100)
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

    def test_template_review_data(self):
        """
        Review template data
        """
        filepath = './tests/contacts.xls'
        template = ImportTemplate.objects.get(name='TEST Contacts all')
        # Review data
        mapping, imported, new, duplicates = template.review_data(filepath, {}, {})

        self.assertEqual(len(mapping), 17)
        self.assertEqual(imported, [])
        self.assertEqual(len(new), 100)
        self.assertEqual(duplicates, [])

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_direct_import_data_from_xls(self, contact_group_check_mock):
        """
        Import data from xls file
        """
        with self.settings(SITE_ENVIRONMENT='prod'):
            before_contacts = Contact.objects.count()
            filepath = './tests/contacts.xls'
            template = ImportTemplate.objects.get(name='TEST Contacts all')
            template.direct_import_data(filepath)
            after_contacts = Contact.objects.count()

            self.assertEqual(before_contacts, 0)
            self.assertEqual(after_contacts, 100)
            self.assertEqual(contact_group_check_mock.call_count, 100)

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_import_duplication_contacts_from_xml(self, contact_group_check_mock):
        """
        Import data from xls file
        """
        with self.settings(SITE_ENVIRONMENT='prod'):
            # Creating contacts for the first time
            filepath = './tests/contacts.xls'
            template = ImportTemplate.objects.get(name='TEST Contacts all')
            template.direct_import_data(filepath)

            # Preparing to import duplicate contacts
            duplication_filepath = './tests/duplicates.xls'

            duplicates = template.prepare_import(duplication_filepath)
            self.assertEqual(len(duplicates), 10)


class TestImportMapping(BasicTestCase):

    def test_import_mapping_methods(self):
        """
        Testing mapping fields
        """
        template = ImportTemplate.objects.get(name='TEST Contacts all')
        title_mapping = template.importmapping_set.first()
        title_mapping.clear_groupmap_cache()
        title_mapping.group_separator = ';'
        title_mapping.save()

        django_field = title_mapping.get_django_field()

        mapping = ImportMapping.objects.get(field= 'title')

        self.assertIsInstance(django_field, models.CharField)
        self.assertIsNone(title_mapping._groupmap_cache,)
        self.assertEqual(mapping.group_separator, ';')
        self.assertEqual(title_mapping.get_field(), 'title')
        self.assertEqual(template.importmapping_set.all().count(), 17)

    def test_import_mapping_country_and_regions(self):
        template = ImportTemplate.objects.get(name='TEST Contacts all')
        country_mapping = template.importmapping_set.get(field='country')

        # Test unicode cast
        # find country by id
        result1 = country_mapping.get_country_value(b'de')
        result2 = country_mapping.get_country_value('de')

        # find country by similar text and ISO EXPANSIONS
        result3 = country_mapping.get_country_value('ermany')
        result4 = country_mapping.get_country_value('united states')

        # Not find country and regions
        result5 = country_mapping.get_country_value('gArmany')
        result6 = country_mapping.get_country_value('DI')
        unknown = country_mapping.get_region_value(None)

        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)
        self.assertIsNotNone(result3)
        self.assertIsNotNone(result4)
        self.assertIsNone(result5)
        self.assertIsNone(result6)
        self.assertIsNone(unknown)


class TestImportSelectorModel(BasicTestCase):

    def test_import_selector_creation(self):
        template = ImportTemplate.objects.get(name='TEST Contacts all')

        count_before = ImportSelector.objects.count()
        for header, value in [('Country', 'Germany'), ('Region', 'Berlin')]:
            selector = factory_import_selector(template, {
                'header': header,
                'value': value,
                'case_sensitive': False
            })
            selector.save()
        count_after = ImportSelector.objects.count()

        self.assertEqual(count_before + 2, count_after)

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_import_direct_with_selectors(self, contact_group_check_mock):
        """
        Test import with column selector, where Country is Germany
        """
        with self.settings(SITE_ENVIRONMENT='prod'):
            template = ImportTemplate.objects.get(name='TEST Contacts all')

            selector = factory_import_selector(template, {
                'header': 'Country',
                'value': 'Germany',
                'case_sensitive': False
            })
            selector.save()

            filepath = './tests/contacts.xls'
            template = ImportTemplate.objects.get(name='TEST Contacts all')
            template.direct_import_data(filepath)
            contact_count = Contact.objects.count()

            self.assertEqual(contact_count, 51)


class TestImportGroupMapping(BasicTestCase):

    def test_Group_mapping_creation(self):
        """
        Add a new group mapping to template
        """
        template = ImportTemplate.objects.get(name='TEST Contacts all')
        mapping_groups = template.importmapping_set.get(field='groups')
        contact_group = ContactGroup.objects.get(name='Public NL-unsubscribed')

        g_mapping = ImportGroupMapping(mapping=mapping_groups,
                                       value='Public NL-unsubscribed', group=contact_group)
        g_mapping.save()

        count_g_mapping = ImportGroupMapping.objects.count()
        self.assertEqual(count_g_mapping, 3)


class TestImportModel(BasicTestCase):
    """
    Test stores an excel file and selects which import template to use when importing
    the data.
    """
    pass
