# coding=utf-8
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls.base import reverse

from djangoplicity.contacts.admin import ImportAdmin
from djangoplicity.contacts.models import ImportTemplate, Import
from tests.factories import factory_request_data, factory_invalid_data

try:
    from mock import patch, MagicMock
except ImportError:
    from unittest.mock import patch, MagicMock


class BasicTestCase(TestCase):
    fixtures = ['actions', 'initial']
    instance = None
    template = None
    filepath = "./tests/contacts.xls"

    def setUp(self):
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@newsletters.org',
            password='password123'
        )
        self.template = ImportTemplate.objects.get(name='TEST Contacts all')
        self.client.force_login(self.admin_user)
        self._import_initial_contacts()

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def _import_initial_contacts(self, contactgroup_change_check):
        with self.settings(SITE_ENVIRONMENT='prod'), open(self.filepath) as contacts_file:
            data = {
                "template": self.template,
                "data_file": SimpleUploadedFile(contacts_file.name, bytes(contacts_file.read())),
            }
            self.instance = Import(**data)
            self.instance.save()
            self.instance.direct_import_data()


class TestImportAdminViews(BasicTestCase):

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_import_create_view(self, contactgroup_change_check_mock):
        with self.settings(SITE_ENVIRONMENT='prod'), open("./tests/contacts.xls") as contacts_file:
            data = {
                "template": self.template,
                "data_file": SimpleUploadedFile(contacts_file.name, bytes(contacts_file.read())),
                "submit": "Submit",
            }
            response = self.client.post(reverse('admin:contacts_import_add'), data)
            self.assertEqual(response.status_code, 200)

    def test_import_preview_view(self):
        response = self.client.get(reverse('admin:contacts_import_preview', kwargs={'pk': self.instance.pk}))
        self.assertEqual(response.status_code, 200)

    @patch('djangoplicity.contacts.tasks.import_data.delay', raw=True)
    def test_import_import_view(self, import_data_mock):
        # Extract data from excel rows
        rows = [r for r in self.template.extract_data(self.filepath)]
        # Create request data
        requests_data = factory_request_data(rows, limit=2)
        # Send data to contact import
        response = self.client.post(reverse('admin:contacts_import', kwargs={'pk': self.instance.pk}), requests_data)
        self.assertEqual(response.status_code, 200)

        # Send invalid data
        invalid_request_data = factory_invalid_data()
        response = self.client.post(reverse('admin:contacts_import', kwargs={'pk': self.instance.pk}), invalid_request_data)
        self.assertEqual(response.status_code, 200)

    @patch('djangoplicity.contacts.tasks.prepare_import.delay', raw=True)
    def test_import_import_review(self, prepare_import_mock):
        response = self.client.get(reverse('admin:contacts_import_review', kwargs={'pk': self.instance.pk}))
        self.assertEqual(response.status_code, 200)

    def test_import_import_live_review(self):
        response = self.client.get(reverse('admin:contacts_import_live_review', kwargs={'pk': self.instance.pk}))
        self.assertEqual(response.status_code, 200)
