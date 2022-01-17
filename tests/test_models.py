# coding=utf-8
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from djangoplicity.contacts.models import Label, LabelRender, Contact, Field, GroupCategory, CountryGroup, PostalZone, \
    Country, Region, ContactGroup, ContactGroupAction
from .factories import factory_label, factory_contact, \
    contacts_count, factory_field, factory_contact_group

try:
    from mock import patch, MagicMock
except ImportError:
    from unittest.mock import patch, MagicMock


class LabelTestCase(TestCase):
    """
    Test Label model
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

    def test_create_label(self):
        """
        Test that a user can create a new label.
        """
        # Before label count
        count_before = Label.objects.count()

        label = factory_label({
            "name": "Standard - 99.1x38.1",
            "paper": "us-letter-5162",
            "enabled": True
        })
        label.save()
        label_render = label.get_label_render()
        label.refresh_from_db()
        # After label Count
        count_after = Label.objects.count()
        self.assertIsInstance(label_render, LabelRender)
        self.assertNotEqual(label.id, None)
        self.assertEqual(str(label), "Standard - 99.1x38.1")
        self.assertEqual(count_before+1, count_after)

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async')
    def test_get_label_render(self, contact_group_check_mock):
        """
        Test renders labels from a contact.
        """
        label = factory_label({
            "name": "Standard - 99.1x38.1",
            "paper": "us-letter-5162",
            "enabled": True,
            "repeat": 3
        })
        label.save()

        contact = factory_contact({
            "id": 5000,
            "first_name": "Jhon",
            "last_name": "Doe",
            "email": "jhondoe@mail.com"
        })
        contact.save()

        qs = Contact.objects.filter(pk=contact.pk)
        # Get rendered PDF to a HttpResponse object.
        render = label.get_label_render().render_http_response(
            qs, 'contact_label_%s.pdf' % contact.pk)
        # Get file path of rendered PDF to a file in a output directory.
        file_path = label.get_label_render().render_file(
            qs, 'contact_label_%s.pdf' % contact.pk
        )

        self.assertIn('/contact_label_5000.pdf', file_path)
        self.assertIn("ReportLab Generated PDF document", render.content)


class FieldTestCase(TestCase):
    """
    Tests Field model, definition of extra fields defined on contact model.
    """

    def setUp(self):
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@newsletters.org',
            password='password123'
        )
        self.client.force_login(self.admin_user)

    def test_field_creation(self):
        """
        Test that one user can create a new extra fields
        """
        before_count = Field.objects.count()
        for i in range(0, 3):
            field = factory_field({
                "slug": "field-%s" % i,
                "name": "test field %s" % i
            })
            field.save()
        after_count = Field.objects.count()
        try:
            field = Field.objects.get(slug="field-1")
        except Field.DoesNotExist:
            field = None

        self.assertEqual(before_count+3, after_count)
        self.assertIsNotNone(field)
        self.assertIsInstance(field, Field)
        self.assertEqual(str(field), "test field 1")

    def test_field_class_methods(self):
        """
        Test Field methods
        """

        # Reset Field cache
        Field._allowed_fields = None

        # Add 5 extra fields
        for i in range(0, 5):
            field = factory_field({
                "slug": "field-%s" % i,
                "name": "test field %s" % i
            })
            field.save()

        field_options = Field.field_options()
        allow_fields = Field.allowed_fields()

        self.assertIsInstance(field_options, list)
        self.assertEqual(len(field_options), 5)
        self.assertIn("field-1", allow_fields)


class LoadBasicDataTestCase(TestCase):
    """
    Test Country, Region PostalZone and CountryGroup models
    """
    fixtures = ['actions', 'initial']

    def test_load_initial_data(self):
        group_category = GroupCategory.objects.get(name='Electronic Distribution')
        country_group = CountryGroup.objects.get(name='Latin_America')
        postal_zone = PostalZone.objects.get(name='World')
        usa = Country.objects.get(name='USA')
        germany = Country.objects.get(iso_code='DE')
        region = Region.objects.get(code='NY')

        # test get zip codes
        new_york_zip_code = usa.get_zip_city('001', '10')
        berlin_zip_code = germany.get_zip_city('10', '115')

        self.assertEqual(new_york_zip_code, '10 001')
        self.assertEqual(berlin_zip_code, '10 115')

        # test country index method
        country_keys = Country.country_index().keys()
        self.assertEqual(country_keys, ['DE', 'US'])

        # test to save in lowercase save method must be transformed to uppercase
        usa.iso_code = 'us'
        usa.save()
        self.assertEqual(usa.iso_code, 'US')

        # test human-readable representation of the models
        self.assertEqual(str(postal_zone), 'World')
        self.assertEqual(str(country_group), 'Latin_America')
        self.assertEqual(str(group_category), 'Electronic Distribution')
        self.assertEqual(str(usa), 'USA')
        self.assertEqual(str(region), 'New York')


class ContactTestCase(TestCase):
    """
    Unit Test to contact model
    """
    fixtures = ['actions', 'initial']
    contact = None
    before_contact_count = 0
    after_contact_count = 0

    def setUp(self):
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@newsletters.org',
            password='password123'
        )
        self.client.force_login(self.admin_user)

    def tearDown(self):
        Field.objects.all().delete()

    @classmethod
    def create_contact(cls, data):
        """
        Method to create a Contact.
        """
        cls.before_contact_count = contacts_count()
        cls.contact = factory_contact(data)
        cls.contact.save()
        cls.after_contact_count = contacts_count()

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_raw_creation_contact(self, contact_group_check_mock):
        ContactTestCase.create_contact({
            "first_name": "Jhon",
            "last_name": "Doe",
            "email": "jhondoe@mail.com"
        })
        contacts = Contact.objects.filter(email="jhondoe@mail.com")

        self.assertTrue(contact_group_check_mock.called)
        self.assertIsNotNone(contacts)
        self.assertIsInstance(contacts[0], Contact)
        self.assertEqual(contacts[0].email, "jhondoe@mail.com")
        self.assertEqual(ContactTestCase.before_contact_count+1, ContactTestCase.after_contact_count)

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=False)
    def test_create_contact(self, contact_group_check_mock):
        ContactTestCase.create_contact({
            "id": 4000,
            "first_name": "Larry",
            "last_name": "Doe",
            "email": "larrydoe@mail.com"
        })

        contact_group_check_mock.assert_called_with(
            ([], 4000, 'larrydoe@mail.com'), countdown=20)

        contacts = Contact.objects.filter(email="larrydoe@mail.com")

        self.assertTrue(contact_group_check_mock.called)
        self.assertIsNotNone(contacts)
        self.assertIsInstance(contacts[0], Contact)
        self.assertEqual(contacts[0].email, "larrydoe@mail.com")
        self.assertEqual(ContactTestCase.before_contact_count + 1, ContactTestCase.after_contact_count)


    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_contact_class_methods(self, contact_group_check_mock):
        """
        Test Contact class methods
        """
        # Reset Field cache
        Field._allowed_fields = None

        # Add extra fields
        for i in range(0, 5):
            field = factory_field({
                "slug": "field-%s" % i,
                "name": "test field %s" % i
            })
            field.save()

        # Create a contact
        Contact.find_or_create_object(**{
            "first_name": "Jhon",
            "last_name": "Doe",
            "email": "jhondoe@mail.com"
        })

        # exec contact class methods
        contact_wanted = Contact.find_object(email='jhondoe@mail.com')
        fields_slugs = Contact.get_allowed_extra_fields()
        language_code = Contact.get_language_code('English')

        self.assertIsInstance(contact_wanted, Contact)
        self.assertEqual(language_code, 'en')
        self.assertIn('field-1', fields_slugs)

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_find_contact_by_id_or_email(self, contact_group_check_mock):
        """
        Find contact by id or email
        """
        # Create contacts with similar data
        for i in range(2000, 2005):
            ContactTestCase.create_contact({
                "id": i,
                "first_name": "Jhon",
                "last_name": "Doe",
                "email": "jhondoe@mail.com"
            })

        # Find contacts methods
        contact_wanted_by_email = Contact.find_object(email='jhondoe@mail.com')
        contact_wanted_by_id = Contact.find_object(id=2001)
        contact_wanted_by_uid = Contact.from_uid('VXXl')
        contacts = Contact.get_contacts_with_email('jhondoe@mail.com')

        # UID Hashids to encrypt the Contact's ID into a unique string
        uid = contact_wanted_by_id.get_uid()

        self.assertEqual(uid, 'VXXl')
        self.assertIsInstance(contact_wanted_by_uid, Contact)
        self.assertIsInstance(contact_wanted_by_email, Contact)
        self.assertIsInstance(contact_wanted_by_id, Contact)
        self.assertIsInstance(contacts[0], Contact)

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_create_contact_and_add_group(self, contact_group_check_mock):
        """
        Create a contact and add it to a group at the same time
        """

        for i in range(200, 203):
            cg = factory_contact_group({
                'id': i,
                'name': 'Test Group %s' % i,
                'order': 1
            })
            cg.save()

        # Create contact and add it to the groups by the group ids
        contact1 = Contact.create_object(groups=[200, 201, 202], **{
            "first_name": "Jhon",
            "last_name": "Doe",
            "email": "jhondoe@mail.com"
        })

        # Create contact and add it to the groups by the group names
        contact2 = Contact.create_object(groups=['Test Group 200', 'Test Group 201'], **{
            "first_name": "Larry",
            "last_name": "Doe",
            "email": "larrydoe@mail.com"
        })

        self.assertIsInstance(contact1, Contact)
        self.assertIsInstance(contact2, Contact)
        self.assertEqual(contact1.groups.count(), 3)
        self.assertEqual(contact2.groups.count(), 2)

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_update_contact(self, contact_group_check_mock):

        # Create contacts groups
        for i in range(200, 203):
            cg = factory_contact_group({
                'id': i,
                'name': 'Test Group %s' % i,
                'order': 1
            })
            cg.save()

        field = factory_field({
            "slug": "company_email",
            "name": "Company Email"
        })
        field.save()

        # Create contact and add it to the groups by the group ids
        country = Country.objects.get(name='USA')
        region = Region.objects.get(name='New York')

        contact = Contact.create_object(groups=[200], **{
            "first_name": "Jhon",
            "last_name": "Doe",
            "email": "jhondoe@mail.com",
            "company_email": "jhondoe@colacola.com",
            'country': country.id,
            'region': region.pk
        })

        # Update contact data country code DE-> Germany, region 556 Berlin
        contact.update_object(groups=[201, 202], country='DE', region=556)
        contact.save()

        # Check update result
        contact1 = Contact.objects.get(email='jhondoe@mail.com')
        self.assertEqual(contact1.country.name, 'Germany')
        self.assertEqual(contact1.region.name, 'Berlin')

        # Update contact data country code DE-> Germany, region 556 Berlin
        contact.update_object(
            groups=[201, 202],
            country='usa',
            region='new york',
            company_email="jhondoe@pepsi.com")
        contact.save()

        contact1.refresh_from_db()
        self.assertEqual(contact1.country.name, 'USA')
        self.assertEqual(contact1.region.name, 'New York')

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_unicode_contact_representation(self, contact_group_check_mock):
        """
        Human-readable representation of the contact model
        """
        contacts_data = [{
                "title": "Mr",
                "first_name": "Jhon",
                "last_name": "Doe",
                "email": "jhondoe@mail.com",
                "organisation": "",
                "department": ""
            },
            {
                "first_name": "",
                "last_name": "",
                "email": "cocacola@mail.com",
                "organisation": "Coca Cola",
                "department": ""
            },
            {
                "first_name": "",
                "last_name": "",
                "email": "hiring@mail.com",
                "organisation": "",
                "department": "Hiring"
            },
            {
                "id": 1000,
                "first_name": "",
                "last_name": "",
                "email": "unknown@mail.com",
                "organisation": "",
                "department": ""
            }
        ]
        for data in contacts_data:
            ContactTestCase.create_contact(data)

        contact1 = Contact.objects.get(email="jhondoe@mail.com")
        contact2 = Contact.objects.get(email="cocacola@mail.com")
        contact3 = Contact.objects.get(email="hiring@mail.com")
        contact4 = Contact.objects.get(email="unknown@mail.com")

        self.assertEqual(str(contact1), "Mr Jhon Doe")
        self.assertEqual(str(contact2), "Coca Cola")
        self.assertEqual(str(contact3), "Hiring")
        self.assertEqual(str(contact4), "1000")

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    @patch('djangoplicity.contacts.signals.contact_removed.send_robust')
    def test_contact_deletion(self, contactgroup_change_check_mock, contact_removed_mock):
        # Create contacts groups
        for i in range(200, 203):
            cg = factory_contact_group({
                'id': i,
                'name': 'Test Group %s' % i,
                'order': 1
            })
            cg.save()

        contact = Contact.create_object(groups=[200, 201, 202], **{
            "first_name": "Jhon",
            "last_name": "Doe",
            "email": "jhondoe@mail.com",
            'country': "germany",
            'region': "berlin"
        })

        contact.delete()

        try:
            contact1 = Contact.objects.get(email="jhondoe@gmail.com")
        except Contact.DoesNotExist:
            contact1 = None
        self.assertTrue(contact_removed_mock.called)
        self.assertIsNone(contact1)

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async')
    def test_get_data(self, contact_group_check_mock):
        ContactTestCase.create_contact({
            "first_name": "Jhon",
            "last_name": "Doe",
            "email": "markdoe@mail.com",
            "language": "en"
        })
        contact = Contact.objects.get(email="markdoe@mail.com")
        data = contact.get_data()
        lang = contact.get_language()

        self.assertTrue(contact_group_check_mock.called)
        self.assertIsInstance(data, dict)
        self.assertEqual(lang, "English")
        self.assertEqual(data['email'], "markdoe@mail.com")

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async')
    def test_contact_extra_fields(self, contact_group_check_mock):
        ContactTestCase.create_contact({
            "first_name": "Jhon",
            "last_name": "Doe",
            "email": "markdoe@mail.com",
            "language": "en"
        })
        contact = Contact.objects.get(email="markdoe@mail.com")

        field1 = factory_field({
            "slug": "company-email",
            "name": "Company Email"
        })

        field2 = factory_field({
            "slug": "personal-email",
            "name": "Personal Email"
        })
        field1.save()
        field2.save()

        # Valid extra field set and get
        contact.set_extra_field("company-email", "markdoe@pear.com")
        company_email = contact.get_extra_field("company-email")

        # Unset extra field
        unset_extra_field = contact.get_extra_field("personal-email")
        self.assertIsNone(unset_extra_field)
        self.assertEqual(company_email, "markdoe@pear.com")

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async')
    def test_contact_groups(self, contact_group_check_mock):
        # create contact group with order 1
        ContactTestCase.create_contact({
            "first_name": "Jhon",
            "last_name": "Doe",
            "email": "markdoe@mail.com",
            "language": "en"
        })
        contact = Contact.objects.get(email="markdoe@mail.com")

        for i in range(0, 5):
            contact_group = factory_contact_group({
                'name': 'test-group-%s' % i,
                'order': i
            })
            contact_group.save()
            contact.groups.add(contact_group)

        groups = contact.get_groups()
        self.assertEqual(len(groups), 5)


class TestContactGroup(TestCase):
    fixtures = ['actions', 'initial']

    def setUp(self):
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@newsletters.org',
            password='password123'
        )
        self.client.force_login(self.admin_user)

    @patch('djangoplicity.contacts.models.ContactGroup.post_save_callback', raw=False)
    def test_contact_group_creation(self, post_save_callback_mock):
        cg = factory_contact_group({
            'name': 'test-group',
            'order': 1
        })
        cg.save()

        contact_group = ContactGroup.objects.get(name='test-group')
        self.assertIsInstance(contact_group, ContactGroup)
        self.assertEqual(str(contact_group), 'test-group')

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async')
    def test_contact_group_features(self, contactgroup_change_check_mock):
        """
        Test get contact emails and exclude -invalid mails
        """

        # create contact group with order 1
        contact_group = factory_contact_group({
            'name': 'test-group',
            'order': 1
        })
        contact_group.save()

        # Create 15 contacts 10 with valid email and 5 with a invalid email
        for i in range(0, 15):
            if i < 10:
                email = "testemail%s@mail.com" % i
            else:
                email = "testemail%s@mail.com-invalid" % i

            contact = factory_contact({
                "first_name": "Test %s" % i,
                "last_name": "Contact",
                "email": email,
                "language": "en",
                "group_order": 5
            })
            contact.save()
            contact.groups.add(contact_group)

        # Get contacts emails set in Contact Group
        emails = contact_group.get_emails()

        self.assertEqual(len(emails), 10)
        self.assertIn('testemail1@mail.com', emails)
        self.assertNotIn('testemail12@gmail.com-invalid', emails)

        # Change group order 1 -> 2
        contact_group.order = 2
        contact_group.save()
        contact = Contact.objects.get(email='testemail1@mail.com')
        self.assertEqual(contact.group_order, 2)

        # Change group order 2 -> 1
        contact_group.order = 1
        contact_group.save()
        contact = Contact.objects.get(email='testemail1@mail.com')
        self.assertEqual(contact.group_order, 1)

        # Delete contact group
        contact_group.delete()
        contact.refresh_from_db()
        self.assertEqual(contact.group_order, None)


class TestContactGroupAction(TestCase):
    """
    Test Contact Group Action
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

    @patch('djangoplicity.contacts.signals.contact_added.send')
    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async')
    def test_event_action_added_to_group(self, task_contactgroup_change_check_mock, signal_contact_added_mock):
        """
        Create a contact and add to distribution group.
        """
        # Get electronic distribution group
        contact_group = ContactGroup.objects.get(name='Public NL')

        # Simulate production environment
        with self.settings(SITE_ENVIRONMENT='prod'):
            contact = Contact.create_object(groups=[contact_group.id], **{
                "first_name": "Jhon",
                "last_name": "Doe",
                "email": "jhondoe@mail.com",
                'country': "germany",
                'region': "berlin"
            })

            self.assertTrue(task_contactgroup_change_check_mock.called)
            self.assertTrue(signal_contact_added_mock.called)

            task_contactgroup_change_check_mock.assert_called_with(
                ([], contact.id, 'jhondoe@mail.com'), countdown=20)

            signal_contact_added_mock.assert_called_with(
                contact=contact, group=contact_group, sender=Contact
            )

            self.assertIsInstance(contact, Contact)

    def test_contact_group_action_class_methods(self):
        """
        Test contact group actions class methods
        """
        contact_group = ContactGroup.objects.get(name='Public NL')
        actions_for_group = ContactGroupAction.get_actions(group=contact_group)
        actions_for_event = ContactGroupAction.get_actions_for_event(on_event='contact_added')

        self.assertEqual(len(actions_for_group), 4)
        self.assertEqual(len(actions_for_event), 1)

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async')
    def test_contact_added_callback(self, task_contact_group_change_check_mock):
        """
        Test handler for when a contact is *added* to a group. Will execute defined actions for this group.
        """
        with self.settings(SITE_ENVIRONMENT='prod'):
            group = ContactGroup.objects.get(name='Public NL')
            from djangoplicity.mailinglists.tasks.mailchimp_actions import MailChimpSubscribeAction

            # Catch MailChimp subscribe action
            MailChimpSubscribeAction.dispatch = MagicMock(return_value=True)

            # Create a contact in one distribution mailchimp list
            contact = Contact.create_object(groups=[group.id], **{
                "first_name": "Jhon",
                "last_name": "Doe",
                "email": "jhondoe@mail.com",
                'country': "germany",
                'region': "berlin"
            })
            # Ensure that actions methods are called
            self.assertTrue(task_contact_group_change_check_mock.called)
            self.assertTrue(MailChimpSubscribeAction.dispatch.called)

            # Validate that the actions arguments are correct
            MailChimpSubscribeAction.dispatch.assert_called_with(
                {
                    'double_optin': False,
                    'send_welcome': False,
                    'list_id': u'12345abcdf'
                },
                contact=contact,
                group=group)

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async')
    def test_contact_removed_callback(self, task_contact_group_change_check_mock):
        """
        Test handler for when a contact is *removed* from a group. Will execute defined actions for this group.
        """
        with self.settings(SITE_ENVIRONMENT='prod'):
            group = ContactGroup.objects.get(name='Public NL')
            from djangoplicity.mailinglists.tasks.mailchimp_actions import MailChimpUnsubscribeAction

            # Catch MailChimp unsubscribe action
            MailChimpUnsubscribeAction.dispatch = MagicMock(return_value=True)

            # Create a contact in one distribution mailchimp list
            contact = Contact.create_object(groups=[group.id], **{
                "first_name": "Jhon",
                "last_name": "Doe",
                "email": "jhondoe@mail.com",
                'country': "germany",
                'region': "berlin"
            })
            # Delete contact
            contact.delete()

            # Ensure that actions methods are called
            self.assertTrue(task_contact_group_change_check_mock.called)
            self.assertTrue(MailChimpUnsubscribeAction.dispatch.called)

            # Validate that the actions arguments are correct
            MailChimpUnsubscribeAction.dispatch.assert_called_with(
                {
                    'send_goodbye': False,
                    'list_id': u'12345abcdf',
                    'delete_member': False
                },
                email='jhondoe@mail.com',
                contact=contact,
                group=group)

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async')
    def test_contact_updated_callback(self, task_contact_group_change_check_mock):
        """
        Test handler for when a local field is *updated*. Will execute defined actions for all groups for this contact.
        """
        with self.settings(SITE_ENVIRONMENT='prod'):
            group = ContactGroup.objects.get(name='Public NL')
            from djangoplicity.mailinglists.tasks.mailchimp_actions import MailChimpUpdateAction

            # Create a contact in one distribution mailchimp list
            contact = Contact.create_object(groups=[group.id], **{
                "first_name": "Jhon",
                "last_name": "Doe",
                "email": "jhondoe@mail.com",
                'country': "germany",
                'region': "berlin"
            })
            # Catch MailChimp update action
            MailChimpUpdateAction.dispatch = MagicMock(return_value=True)

            # update fields contact
            dirty_fields = {
                "first_name": "Larry",
                "last_name": "Doe",
                "email": "larrydoe@mail.com"
            }
            contact.update_object(**dirty_fields)
            contact.save()

            # Ensure that actions methods are called
            self.assertTrue(task_contact_group_change_check_mock.called)
            self.assertTrue(MailChimpUpdateAction.dispatch.called)

            # Validate that the actions arguments are correct
            MailChimpUpdateAction.dispatch.assert_called_with(
                {
                    'double_optin': False,
                    'send_welcome': False,
                    'send_goodbye': False,
                    'list_id': u'12345abcdf',
                    'delete_member': False
                },
                changes={
                    'first_name': ('Jhon', 'Larry'),
                    'email': ('jhondoe@mail.com', 'larrydoe@mail.com')
                },
                instance=contact
            )
