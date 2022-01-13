from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.test.testcases import TransactionTestCase
from djangoplicity.contacts.models import ImportTemplate, Import

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


class TestDeduplicationBase(TransactionTestCase):
    fixtures = ['actions', 'initial']
    instance = None
    template = None

    def setUp(self):
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@newsletters.org',
            password='password123'
        )
        self.client.force_login(self.admin_user)
        self.template = ImportTemplate.objects.get(name='TEST Contacts all')
        # load 10 duplicate contacts
        self._import_contacts("./tests/data_sources/duplicates.xls")
        # load 100 contacts
        self._import_contacts("./tests/data_sources/contacts.xls")

    @patch('djangoplicity.contacts.signals.contact_added.send')
    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def _import_contacts(self, filepath, contactgroup_change_check, contact_added_mock):
        # Method to load contacts by filepath
        with self.settings(SITE_ENVIRONMENT='prod'), open(filepath) as contacts_file:
            data = {
                "template": self.template,
                "data_file": SimpleUploadedFile(contacts_file.name, bytes(contacts_file.read())),
            }
            self.instance = Import(**data)
            self.instance.save()
            self.instance.direct_import_data()