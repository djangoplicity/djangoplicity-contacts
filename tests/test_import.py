# coding=utf-8
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.test import Client
from djangoplicity.contacts.admin import ImportAdmin
from djangoplicity.contacts.models import Contact, ContactGroup, ImportTemplate, ImportMapping, \
    ImportSelector, ImportGroupMapping, DataImportError, Import
from .factories import factory_import_selector, factory_request_data
from djangoplicity.contacts.importer import CSVImporter, ExcelImporter
from djangoplicity.contacts.tasks import prepare_import
import json
from django.core import mail

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

    def test_bad_file_format(self):
        # Raise exception with invalid file format
        filepath = './tests/contacts.pdf'
        template = ImportTemplate.objects.get(name='TEST Contacts all')
        self.assertRaises(DataImportError, template.get_importer, filepath)

    def test_bad_column_in_file(self):
        # Raise bad column exception
        filepath = './tests/bad_column.xls'
        template = ImportTemplate.objects.get(name='TEST Contacts all')
        row, data = template.preview_data(filepath)

        count_errors = 0
        for row in data:
            if 'ERROR' in row:
                count_errors += 1

        self.assertEqual(10, count_errors)
        self.assertIsNotNone(data)

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

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_import_creation(self, contactgroup_change_check_mock):
        # Create an import model instance
        with self.settings(SITE_ENVIRONMENT='prod'), open("./tests/contacts.xls") as contacts_file:
            import_count_before = Import.objects.count()
            contacts_count_before = Contact.objects.count()
            template = ImportTemplate.objects.get(name='TEST Contacts all')
            data = {
                "template": template,
                "data_file": SimpleUploadedFile(contacts_file.name, bytes(contacts_file.read())),
            }
            instance = Import(**data)
            instance.save()

            imported = instance.direct_import_data()
            import_count_after = Import.objects.count()
            contacts_count_after = Contact.objects.count()

            columns, rows = instance.preview_data()

            self.assertTrue(imported)
            self.assertEqual(contacts_count_after, contacts_count_before + 100)

            self.assertEqual(import_count_before+1, import_count_after)
            self.assertEqual(18, len(columns))
            self.assertEqual(100, len(rows))
            self.assertIsInstance(instance, Import)


class TestImportMethodsModel(BasicTestCase):
    """
    Test Import methods in import model
    """
    import_instance = None
    response = None
    template = None

    def setUp(self):
        super(TestImportMethodsModel, self).setUp()
        # set initial contacts to test duplicates behavior
        self.template = ImportTemplate.objects.get(name='TEST Contacts all')
        self._import_initial_contacts()
        self._import_contacts()

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def _import_initial_contacts(self, contactgroup_change_check):
        # Create an import model instance
        with self.settings(SITE_ENVIRONMENT='prod'), open("./tests/duplicates.xls") as contacts_file:
            data = {
                "template": self.template,
                "data_file": SimpleUploadedFile(contacts_file.name, bytes(contacts_file.read())),
            }
            instance = Import(**data)
            instance.save()
            instance.direct_import_data()

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def _import_contacts(self, contactgroup_change_check):
        # Create an import model instance
        with self.settings(SITE_ENVIRONMENT='prod'), open("./tests/contacts.xls") as contacts_file:
            data = {
                "template": self.template,
                "data_file": SimpleUploadedFile(contacts_file.name, bytes(contacts_file.read())),
            }
            self.import_instance = Import(**data)
            self.import_instance.save()

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_prepare_to_import(self, contactgroup_change_check_mock):
        with self.settings(SITE_ENVIRONMENT='prod'):
            prepare_import(self.import_instance.id, 'jhondoe@mail.com')

            response = self.import_instance.prepare_import()
            duplicates = json.loads(self.import_instance.duplicate_contacts)

            # Generate a preview of the data mapping for this import. The data
            # will be used as the basis for the import.
            headers, rows = self.import_instance.preview_data()

            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(mail.outbox[0].subject, 'Import %s (%s) ready for review' %
                             (self.import_instance.pk, self.import_instance.data_file))
            self.assertTrue(response)
            self.assertEqual(len(duplicates), 10)
            self.assertEqual(len(headers), 18)
            self.assertEqual(len(rows), 100)

    def test_review_data(self):
        with self.settings(SITE_ENVIRONMENT='prod'):
            mapping, imported, new, duplicates = self.import_instance.review_data()
            self.assertEqual(len(mapping), 17)
            self.assertEqual(len(new), 100)

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_import_data(self, contactgroup_change_check_mock):
        with self.settings(SITE_ENVIRONMENT='prod'):
            data = factory_request_data()
            mapping, imported, new, duplicates = self.import_instance.review_data()

            import_contacts = ImportAdmin.clean_import_data(data)
            response = self.import_instance.import_data(import_contacts)
            self.import_instance.save()

            self.assertEqual(self.import_instance.status, 'new')
            self.assertTrue(response)

            # test template review data for mapping[1] - phone
            contact = Contact.objects.get(email='jhondoe@cox-ayala.com')
            field_data = self.template._get_review_form_data(mapping[1], contact)
            self.assertEqual(field_data['name'], 'phone')
            self.assertEqual(field_data['value'], '890.067.9460')

            # test template review data for mapping[2] - email
            field_data = self.template._get_review_form_data(mapping[2])
            self.assertEqual(field_data['name'], 'email')
            self.assertIsNone(field_data['value'])
