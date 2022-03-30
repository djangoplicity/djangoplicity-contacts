# coding=utf-8

from django.urls.base import reverse

from djangoplicity.contacts.models import Country
from tests.base import TestDeduplicationBase, BaseContactTestCase, BasicTestCase
from urllib import urlencode

try:
    from mock import patch, MagicMock
except ImportError:
    from unittest.mock import patch, MagicMock


class ContactUpdateViewTestCase(BaseContactTestCase):

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=True)
    def test_contact_update_view(self, contactgroup_change_check_mock):
        data = {
            "first_name": "Larry",
            "last_name": "Doe",
            "email": "larrydoe@mail.com"
        }
        contact = self.create_contact(data)

        update_data = {
            "first_name": "Jon",
            "last_name": "Doe",
            "email": "jondoe@mail.com"
        }
        # request put method with contact uid edit
        response = self.client.put(
            reverse('public_contact_edit', kwargs={'uid': contact.get_uid()}),
            update_data
        )
        contact.refresh_from_db()
        self.assertEqual(response.status_code, 200)


class RegionByCountryJSONViewTestCase(BasicTestCase):

    def test_region_view(self):
        country = Country.objects.first()
        response = self.client.get(reverse('region_by_country', kwargs={'pk': country.pk}))
        self.assertEqual(response.status_code, 200)

