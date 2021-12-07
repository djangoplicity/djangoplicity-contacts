# coding=utf-8
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from djangoplicity.contacts.models import Label, LabelRender, Contact, Field, GroupCategory, CountryGroup, PostalZone, \
    Country, Region, ContactGroup
from .factories import factory_label, factory_contact, \
    contacts_count, factory_field, factory_contact_group

try:
    from mock import patch
except ImportError:
    from unittest.mock import patch


class LabelTestCase(TestCase):
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

    # @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async')
    # def test_get_label_render(self, contact_group_check_mock):
    #     label = factory_label({
    #         "name": "Standard - 99.1x38.1",
    #         "paper": "us-letter-5162",
    #         "enabled": True
    #     })
    #     label.save()
    #     before_contact_count = Contact.objects.count()
    #     contact = factory_contact({
    #         "first_name": "Jhon",
    #         "last_name": "Doe",
    #         "email": "jhondoe@mail.com"
    #     })
    #     contact.save()
    #     after_contact_count = Contact.objects.count()
    #
    #     # qs = Contact.objects.filter(pk=contact.pk)
    #     # render = label.get_label_render().render_http_response(
    #     #     qs, 'contact_label_%s.pdf' % contact.pk)
    #
    #     contact_group_check_mock.assert_called_with(
    #         (contact._initial_groups, contact.pk, contact.email),
    #         countdown=20
    #     )
    #     self.assertTrue(contact_group_check_mock.called)
    #     # self.assertIn("Jhon", render.content)

class FieldTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@newsletters.org',
            password='password123'
        )
        self.client.force_login(self.admin_user)

    def test_field_creation(self):
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


class BasicDataTestCase(TestCase):
    fixtures = ['actions', 'initial']

    def test_basic_data(self):
        group_category = GroupCategory.objects.get(name='Electronic Distribution')
        country_group = CountryGroup.objects.get(name='Latin_America')
        postal_zone = PostalZone.objects.get(name='World')
        usa = Country.objects.get(name='USA')
        germany = Country.objects.get(iso_code='DE')
        new_york_zip_code = usa.get_zip_city('001', '10')
        berlin_zip_code = germany.get_zip_city('10', '115')
        country_keys = Country.country_index().keys()
        region = Region.objects.get(code='NY')

        usa.iso_code = 'us'
        usa.save()

        self.assertIsNotNone(group_category)
        self.assertIsNotNone(country_group)
        self.assertIsNotNone(postal_zone)
        self.assertIsNotNone(usa)
        self.assertIsNotNone(germany)
        self.assertIsNotNone(region)

        self.assertIsInstance(group_category, GroupCategory)
        self.assertIsInstance(country_group, CountryGroup)
        self.assertIsInstance(postal_zone, PostalZone)
        self.assertIsInstance(usa, Country)
        self.assertIsInstance(germany, Country)

        self.assertEqual(str(postal_zone), 'World')
        self.assertEqual(str(country_group), 'Latin_America')
        self.assertEqual(str(group_category), 'Electronic Distribution')
        self.assertEqual(str(usa), 'USA')
        self.assertEqual(str(region), 'New York')

        self.assertEqual(new_york_zip_code, '10 001')
        self.assertEqual(berlin_zip_code, '10 115')
        self.assertEqual(country_keys,  ['DE', 'US'])
        self.assertEqual(usa.iso_code, 'US')


class ContactTestCase(TestCase):
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

    @classmethod
    def create_contact(cls, data):
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
            "first_name": "Larry",
            "last_name": "Doe",
            "email": "larrydoe@mail.com"
        })

        contacts = Contact.objects.filter(email="larrydoe@mail.com")

        self.assertTrue(contact_group_check_mock.called)
        self.assertIsNotNone(contacts)
        self.assertIsInstance(contacts[0], Contact)
        self.assertEqual(contacts[0].email, "larrydoe@mail.com")
        self.assertEqual(ContactTestCase.before_contact_count + 1, ContactTestCase.after_contact_count)

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

        field = factory_field({
            "slug": "company-email",
            "name": "Company Email"
        })
        field.save()

        contact.set_extra_field("company-email", "markdoe@pear.com")
        company_email = contact.get_extra_field("company-email")

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
