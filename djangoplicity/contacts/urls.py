# -*- coding: utf-8 -*-
#
# djangoplicity-contacts
# Copyright (c) 2007-2014, European Southern Observatory (ESO)
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

from djangoplicity.contacts.views import ContactPublicUpdate, \
    RegionByCountryJSONView

from django.conf.urls import url, include

urlpatterns = [
    url( r'^edit/(?P<uid>.*)/$', ContactPublicUpdate.as_view(), name='public_contact_edit' ),
    url(r'^countryregions/(?P<pk>[0-9]+)/json/$', RegionByCountryJSONView.as_view(), kwargs={}, name='region_by_country'),
    url(r'^api/', include('djangoplicity.contacts.api.urls')),
]
