from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.testcases import TransactionTestCase
from djangoplicity.contacts.models import Import, ImportTemplate, Contact, ContactGroup
from djangoplicity.contacts.tasks import direct_import_data, import_data, run_deduplication, contactgroup_change_check, \
    EveryDayAction
from tests.base import TestDeduplicationBase, BasicTestCase, BaseContactTestCase
from tests.factories import factory_request_data, factory_deduplication, factory_contact, factory_contact_group
from django.core import mail
import json

try:
    from mock import patch, MagicMock
except ImportError:
    from unittest.mock import patch, MagicMock


class PeriodicActionTestCase(BasicTestCase):
    fixtures = ['actions', 'initial']

    @patch('djangoplicity.contacts.tasks.SetContactGroupAction.dispatch')
    def test_every_5min_action_run(self, set_contact_group_action_mock):
        action = EveryDayAction()
        action.run()
        self.assertTrue(set_contact_group_action_mock.called)


class ImportTaskTestCase(TransactionTestCase):
    fixtures = ['actions', 'initial']
    filepath = "./tests/data_sources/contacts.xls"

    def setUp(self):
        with open(self.filepath) as contacts_file:
            self.template = ImportTemplate.objects.get(name='TEST Contacts all')
            self.data = {
                "template": self.template,
                "data_file": SimpleUploadedFile(contacts_file.name,
                                                bytes(contacts_file.read())),
            }
            self.instance = Import(**self.data)
            self.instance.save()

    @patch('djangoplicity.mailinglists.tasks.mailchimp_actions.MailChimpSubscribeAction.dispatch')
    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_direct_import_data_task(self, contact_group_check_mock, mailchimp_subscribe_action_mock):
        with self.settings(SITE_ENVIRONMENT='prod'), open("./tests/data_sources/contacts.xls") as contacts_file:
            # Run contacts import in the background and run MailChimp Subscribe Action
            direct_import_data(self.instance.pk)

            self.assertTrue(contact_group_check_mock.called)
            self.assertTrue(mailchimp_subscribe_action_mock.called)
            self.assertEqual(contact_group_check_mock.call_count, 100)

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_import_data_task(self, contact_group_check_mock):
        rows = [r for r in self.template.extract_data(self.filepath)]
        # Create request data
        requests_data = factory_request_data(rows, limit=2)
        import_data(self.instance.id, requests_data)

        self.assertTrue(contact_group_check_mock.called)


class DeduplicationTaskTestCase(TestDeduplicationBase):

    def test_run_deduplication_task(self):
        with self.settings(SITE_ENVIRONMENT='prod'):
            # Look for potential duplicates
            instance = factory_deduplication({})
            instance.save()
            # run celery task
            run_deduplication(instance.id, 'admin@djangoplicity.com')
            instance.refresh_from_db()

            duplicates, total_duplicates = instance.review_data()
            duplicate_contacts = json.loads(instance.duplicate_contacts)

            self.assertEqual(len(duplicate_contacts), 10)
            self.assertEqual(len(duplicates), 10)
            self.assertEqual(total_duplicates, 10)
            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(mail.outbox[0].subject,
                             'Deduplication %s ready for review' % instance.pk)


class ContactTaskTestCase(TransactionTestCase):
    fixtures = ['actions', 'initial']

    @patch('djangoplicity.contacts.models.Contact.pre_save_callback')
    @patch('djangoplicity.contacts.signals.contact_removed.send')
    @patch('djangoplicity.contacts.signals.contact_added.send')
    def test_contact_group_change_check_task(self, contact_added_mock, contact_removed_mock, pre_save_mock):
        """Test that the ``contactgroup_change_check`` task runs with no errors,
        and returns the correct result."""

        for i in range(200, 204):
            cg = factory_contact_group({
                'id': i,
                'name': 'Test Group %s' % i,
                'order': 1
            })
            cg.save()

        # Create contact and add it to the groups by the group ids
        contact = Contact.create_object(groups=[200, 201], **{
            "first_name": "Jon",
            "last_name": "Doe",
            "email": "jhondoe@mail.com"
        })

        # workaround to test this task, not detected group changes in testing
        contactgroup_change_check.apply_async(
            ([202, 203], contact.pk, contact.email), countdown=20,
        )

        self.assertTrue(contact_added_mock.called)
        self.assertEqual(contact_added_mock.call_count, 4)

        self.assertTrue(contact_removed_mock.called)
        self.assertEqual(contact_removed_mock.call_count, 2)

        contact_not_exist_id = 10000
        contactgroup_change_check.apply_async(
            ([202, 203], contact_not_exist_id, contact.email), countdown=20,
        )
        self.assertEqual(contact_added_mock.call_count, 4)


class UpdateContactActionTestCase(BaseContactTestCase):
    # test update contact celery task
    fixtures = ['actions', 'initial']

    @patch('djangoplicity.mailinglists.tasks.mailchimp_actions.MailChimpUpdateAction.dispatch')
    @patch('djangoplicity.mailinglists.tasks.mailchimp_actions.MailChimpSubscribeAction.dispatch')
    def test_run_action(self, mailchimp_subscribe_action_mock, mailchimp_update_action_mock):
        with self.settings(SITE_ENVIRONMENT='prod'):
            # Create contact and add it to the groups by the group ids
            groups_ids = ContactGroup.objects.values_list('id', flat=True)
            contact = Contact.create_object(groups=groups_ids, **{
                "first_name": "Jhon",
                "last_name": "Doe",
                "email": "jhondoe@mail.com"
            })

            contact.first_name = 'Jon'
            contact.email = 'jondoe@mail.com'
            contact.save()

            self.assertEqual(mailchimp_update_action_mock.call_count, 1)
            self.assertEqual(mailchimp_subscribe_action_mock.call_count, 1)

