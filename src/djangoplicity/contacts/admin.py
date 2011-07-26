# -*- coding: utf-8 -*-
#
# djangoplicity-contacts
# Copyright (c) 2007-2011, European Southern Observatory (ESO)
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
#


from django.contrib import admin
from django.utils.translation import ugettext as _
from djangoplicity.contacts.models import ContactGroup, Contact, Country, CountryGroup, GroupCategory, ContactField, Field
from djangoplicity.admincomments.admin import AdminCommentInline, AdminCommentMixin


class CountryAdmin( admin.ModelAdmin ):
	list_display = ['name', 'iso_code', 'dialing_code', ]
	list_editable = ['iso_code', 'dialing_code', ]
	list_filter = ['groups', ]
	search_fields = ['name', 'iso_code', 'dialing_code', ]
	filter_horizontal = ['groups']


class GroupCategoryAdmin( admin.ModelAdmin ):
	list_display = ['name', ]
	search_fields = ['name', ]
	
class FieldAdmin( admin.ModelAdmin ):
	list_display = ['name', ]
	search_fields = ['name', ]

	
class CountryGroupAdmin( admin.ModelAdmin ):
	list_display = ['name', 'category' ]
	search_fields = ['name', 'category__name' ]
	list_filter = ['category', ]

	
class ContactGroupAdmin( admin.ModelAdmin ):
	list_display = ['name', 'category' ]
	search_fields = ['name', 'category__name' ]
	list_filter = ['category', ]
	

class ContactFieldInlineAdmin( admin.TabularInline ):
	model = ContactField
	extra = 1

class ContactAdmin( AdminCommentMixin, admin.ModelAdmin ):
	list_display = ['id','organisation', 'department','street','city','country', 'first_name', 'last_name', 'email', 'phone', 'website', 'created', 'last_modified' ]
	list_editable = ['first_name', 'last_name', 'email', 'organisation','department','street','city','phone','website', ]
	list_filter = ['last_modified', 'groups__category__name', 'groups', 'country__groups', 'extra_fields__name', 'country', 'title' ]
	search_fields = ['first_name', 'last_name', 'title','position', 'email', 'organisation','department','street','city','phone','website','social','extra_fields__contactfield__value' ]
	fieldsets = (
		( None, {
			'fields': ( ('id', 'created', 'last_modified'), )
		}),
		( 'Person', {
			'fields': ( ('title', 'first_name', 'last_name'), 'position', )
		}),
		( 'Address', {
			'fields': ( 'organisation', 'department', 'street', 'city', 'country' )
		}),
		( 'Groups', {
			'fields': ( 'groups', )
		}),
		( 'Contact', {
			'fields': ( 'email', 'phone', 'website', 'social', )
		}),
	)
	filter_horizontal = ['groups']
	readonly_fields = ['id', 'created', 'last_modified']
	inlines = [ ContactFieldInlineAdmin, AdminCommentInline, ]

	
def register_with_admin( admin_site ):
	admin_site.register( Field, FieldAdmin )
	admin_site.register( Country, CountryAdmin )
	admin_site.register( GroupCategory, GroupCategoryAdmin )
	admin_site.register( CountryGroup, CountryGroupAdmin )
	admin_site.register( ContactGroup, ContactGroupAdmin )
	admin_site.register( Contact, ContactAdmin )
		
# Register with default admin site	
register_with_admin( admin.site )