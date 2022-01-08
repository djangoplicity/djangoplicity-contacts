# coding=utf-8
from django.core.management import call_command
from django.test import TestCase
from djangoplicity.contacts.models import Country, Region


class CommandsTestCase(TestCase):
    fixtures = ['countries']

    def test_mycommand(self):
        " Test my custom command."

        args = []
        opts = {}
        call_command('update_regions', *args, **opts)

        regions_count = Region.objects.count()
        self.assertEqual(regions_count, 3107)
