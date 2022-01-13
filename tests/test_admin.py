# coding=utf-8
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import Client
from django.test.client import RequestFactory
from django.test.testcases import TransactionTestCase
from django.urls.base import reverse
from djangoplicity.contrib.admin.sites import AdminSite

from djangoplicity.contacts.admin import ContactAdmin
from djangoplicity.contacts.forms import ContactListAdminForm
from djangoplicity.contacts.models import ImportTemplate, Import, Contact, ContactGroup
from tests.base import TestDeduplicationBase
from tests.factories import factory_request_data, factory_invalid_data, factory_deduplication, \
    factory_deduplication_form, factory_label

import json

try:
    from mock import patch, MagicMock
except ImportError:
    from unittest.mock import patch, MagicMock


class BasicTestCase(TransactionTestCase):
    fixtures = ['actions', 'initial']
    instance = None
    template = None
    filepath = "./tests/data_sources/contacts.xls"

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
        with self.settings(SITE_ENVIRONMENT='prod'), open("./tests/data_sources/contacts.xls") as contacts_file:
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


class TestContactAdmin(TestDeduplicationBase):

    def setUp(self):
        super(TestContactAdmin, self).setUp()
        self.request_factory = RequestFactory()

    def test_contact_label_view(self):
        contact = Contact.objects.first()
        response = self.client.get(reverse('admin:contacts_label', kwargs={'pk': contact.id}))
        self.assertEqual(response.status_code, 200)

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async')
    def test_contact_admin_methods(self, contact_group_check_mock):
        # data sources
        contact = Contact.objects.first()
        response = self.client.get(reverse('admin:contacts_label', kwargs={'pk': contact.id}))
        request = response.wsgi_request
        admin_instance = ContactAdmin(Contact, AdminSite())
        label = factory_label({
            "name": "Standard - 99.1x38.1",
            "paper": "us-letter-5162",
            "enabled": True
        })
        label.save()
        group = ContactGroup.objects.first()

        # ContactAdmin call methods
        actions = admin_instance.get_actions(request)
        change_list_form_class = admin_instance.get_changelist_form(request)
        queryset = admin_instance.get_queryset(request)
        excel_export = admin_instance.action_export_xls(
            modeladmin=None, request=request, queryset=queryset)
        tags = admin_instance.tags(contact)
        label_request = admin_instance.action_make_label(request=request, queryset=queryset, label=label)
        admin_instance.action_set_group(request=request, queryset=queryset,
                                        group=None, remove=True)
        admin_instance.action_set_group(request=request, queryset=queryset,
                                        group=group, remove=False)

        self.assertEqual(tags, 'Public NL, Public NL-invite')
        self.assertEqual(label_request['content-type'], 'application/pdf')
        self.assertEqual(excel_export['content-type'], 'application/vnd.ms-excel')
        self.assertIn('export_xls', actions)
        self.assertEqual(change_list_form_class, ContactListAdminForm)


class TestDeduplicationAdminViews(TestDeduplicationBase):
    instance = None

    def setUp(self):
        super(TestDeduplicationAdminViews, self).setUp()
        self.instance = factory_deduplication({})
        self.instance.save()

    def test_deduplication_review_view(self):
        # Test deduplication admin review view
        response = self.client.get(reverse('admin:contacts_deduplication_review', kwargs={'pk': self.instance.pk}))
        self.assertEqual(response.status_code, 200)

    @patch('djangoplicity.contacts.tasks.run_deduplication.delay', raw=True)
    def test_deduplication_run_view(self, run_deduplication_mock):
        # Run deduplication tasks for given groups
        response = self.client.get(reverse('admin:contacts_deduplication_run', kwargs={'pk': self.instance.pk}))
        self.assertEqual(response.status_code, 302)

    def test_deduplication_deduplicate_view(self):
        # Review and clean the POST data to be used by deduplicate_view
        self.instance.run()
        duplicate_contacts = json.loads(self.instance.duplicate_contacts)
        data = factory_deduplication_form(duplicate_contacts.items()[0:3], 'update')
        data.update(factory_deduplication_form(duplicate_contacts.items()[3:6], 'ignore'))
        data.update(factory_deduplication_form(duplicate_contacts.items()[6:], 'delete'))

        response = self.client.post(
            reverse('admin:contacts_deduplication_review',
                    kwargs={'pk': self.instance.pk}), data)
        self.assertEqual(response.status_code, 200)
