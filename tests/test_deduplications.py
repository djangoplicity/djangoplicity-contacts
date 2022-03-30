from django.test import TestCase

from djangoplicity.contacts.deduplication import is_street, is_organisation, split_addresslines, split_name


class DeDuplicationsTestCase(TestCase):
    fixtures = ['actions', 'initial']

    def test_deduplictions_methods(self):
        # Methods requests
        response_is_street = is_street('63344 Brooke Place Suite 507 nSouth Dale, DC 64431')
        response_is_organization = is_organisation('National Optical-Infrared Astronomy Research Laboratory')
        response_split_name = split_name('Mr. Jon Doe')

        # Assertions
        self.assertEqual(response_split_name, ('Mr.', 'Jon Doe'))
        self.assertTrue(response_is_street)
        self.assertTrue(response_is_organization)

    def test_deduplication_split_address(self):
        line = ['Shepard LLC',
                'Education & Engagement',
                '63344 Brooke Place Suite 507 nSouth Dale, DC 64431',
                '709 Holland Street West Joseph Chester, IL 80579']

        r4 = split_addresslines(line)
        split_addresslines(line[0:3])
        split_addresslines(line[0:1]+line[2:4])
        split_addresslines(line[2:4])
        split_addresslines(line[0:1]+line[2:1])
        split_addresslines(line[0:2])
        split_addresslines(line[2:3])
        r0 = split_addresslines([])

        self.assertEqual(r0, {
            'organisation': '',
            'department': '',
            'street_1': '',
            'street_2': ''
        })

        self.assertEqual(r4, {
            'organisation': 'Shepard LLC',
            'department': 'Education & Engagement',
            'street_1': '63344 Brooke Place Suite 507 nSouth Dale, DC 64431',
            'street_2': '709 Holland Street West Joseph Chester, IL 80579'
        })
