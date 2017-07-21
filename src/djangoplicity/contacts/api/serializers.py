# -*- coding: utf-8 -*-
#
# djangoplicity-contacts
# Copyright (c) 2007-2017, European Southern Observatory (ESO)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
#    * Neither the name of the European Southern Observatory nor the names
#      of its contributors may be used to endorse or promote products derived
#      from this software without specific prior written permission.
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

from __future__ import unicode_literals

import json

from rest_framework import serializers

from djangoplicity.contacts.models import Country, Region, Import, \
	ImportMapping, CONTACTS_FIELDS


class CountrySerializer(serializers.ModelSerializer):
	class Meta:
		model = Country
		fields = ('pk', 'name')


class RegionSerializer(serializers.ModelSerializer):
	class Meta:
		model = Region
		fields = ('pk', 'name', 'country')


class MappingSerializer(serializers.ModelSerializer):
	class Meta:
		model = ImportMapping
		fields = ('header', 'field', 'group_separator')


class ImportSerializer(serializers.ModelSerializer):
	data = serializers.SerializerMethodField(read_only=True)
	duplicate_contacts = serializers.SerializerMethodField(read_only=True)
	imported_contacts = serializers.SerializerMethodField(read_only=True)
	contact_fields = serializers.SerializerMethodField(read_only=True)
	countries = serializers.SerializerMethodField(read_only=True)
	regions = serializers.SerializerMethodField(read_only=True)

	def get_data(self, obj):
		mapping, rows = obj.preview_data()

		return {
			'rows': rows,
			'mapping': MappingSerializer(mapping[1:], many=True).data,
		}

	def get_duplicate_contacts(self, obj):
		if obj.duplicate_contacts:
			return json.loads(obj.duplicate_contacts)
		else:
			return {}

	def get_imported_contacts(self, obj):
		if obj.imported_contacts:
			return json.loads(obj.imported_contacts)
		else:
			return {}

	def get_contact_fields(self, obj):
		return [f for f in CONTACTS_FIELDS if f[0] != 'pk']

	def get_countries(self, obj):
		countries = Country.objects.all()
		return CountrySerializer(countries, many=True).data

	def get_regions(self, obj):
		regions = Region.objects.all()
		return RegionSerializer(regions, many=True).data

	class Meta:
		model = Import
		fields = ('status', 'template', 'data', 'duplicate_contacts',
			'imported_contacts', 'contact_fields', 'countries', 'regions')
