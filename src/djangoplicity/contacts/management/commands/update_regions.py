# -*- coding: utf-8 -*-
#
# djangoplicity-contacts
# Copyright (c) 2007-2015, European Southern Observatory (ESO)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
#   * Neither the name of the European Southern Observatory nor the names
#     of its contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY ESO ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL ESO BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE

import requests

from django.core.management.base import BaseCommand

from djangoplicity.contacts.models import Country, Region


class Command(BaseCommand):
    '''
    Update Regions based on geoname.org's data
    '''
    def handle(self, *args, **options):
        r = requests.get('http://download.geonames.org/export/dump/admin1CodesASCII.txt')

        c = None

        for line in r.text.splitlines():
            code, local_name, name, _uid = line.split('\t')
            country_code, region_code = code.split('.')

            if not c or c.iso_code != country_code:
                try:
                    c = Country.objects.get(iso_code=country_code)
                except Country.DoesNotExist:
                    continue

            region, _created = Region.objects.get_or_create(country=c, code=region_code)
            region.name = name
            region.local_name = local_name

            region.save()
            print 'Updating: %s' % region
