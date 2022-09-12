from djangoplicity.contacts.utils import serialize_contact, \
    print_sideby, joinfields, debug_data
from django.test import TestCase, Client
from tests.factories import factory_contact

try:
    from mock import patch, MagicMock
except ImportError:
    from unittest.mock import patch, MagicMock


class UtilsTestCase(TestCase):
    fixtures = ['actions', 'initial']
    default = {
            "id": 4000,
            "first_name": "Larry",
            "last_name": "Doe",
            "email": "larrydoe@mail.com",
            "street_1": "63344 Brooke Place Suite 507 nSouth Dale, DC 64431"
        }

    @patch('djangoplicity.contacts.tasks.contactgroup_change_check.apply_async', raw=False)
    def create_contact(self, data, contactgroup_change_check_mock):
        contact = factory_contact(data)
        contact.save()
        return contact

    def test_serialize_contact_method(self):
        contact = self.create_contact(self.default)
        # Write serialization of object to output stream
        out_file = open("myfile.json", "w")
        serialize_contact(contact, out_file)
        out_file.close()

        out_file = open("myfile.json", "r")
        data = out_file.read()
        out_file.close()

        # assertions
        self.assertIn('63344 Brooke Place Suite 507 nSouth Dale, DC 64431', data)

    def test_print_side_by_util(self):
        data_a = {
             'address_lines': ['Shepard LLC', 'and Sons', '63344 Brooke Place Suite 507 nSouth Dale, DC 64431',
                               '709 Holland Street\nWest Josephchester, IL 80579'],
             'name': 'Mr. Larry Doe',
             'city': 'North Jason',
             'country': 'USA'
        }
        data_b = {
             'address_lines': ['Mata, Weiss and Mcdonald', 'Group',
                               '3932 Burke Mission Apt. 049 North Laurashire, TX 29309',
                               '131 James Trail\nEast Annetteland, IA 11098'],
             'name': 'Mr. Jon Doe',
             'city': 'Melissamouth',
             'country': 'USA'
        }
        # Set country name
        result = print_sideby(data_a, data_b)
        data = debug_data(data_a)
        j_fields = joinfields('Mr.', 'Jon', 'Doe')
        self.assertIn('Mr. Larry Doe', result)
        self.assertEqual('Mr. Jon Doe', j_fields)
        self.assertIn('West Josephchester, IL 80579', data)
