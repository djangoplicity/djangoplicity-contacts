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

"""
Admin interfaces for contact models.
"""

from django.contrib import admin
from django.utils.translation import ugettext as _
from djangoplicity.contacts.models import ContactGroup, Contact, Country, CountryGroup, GroupCategory, ContactField, Field, Label, PostalZone, ContactGroupAction
from djangoplicity.admincomments.admin import AdminCommentInline, AdminCommentMixin
from django.conf.urls.defaults import patterns
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.defaultfilters import slugify
from djangoplicity.contacts.signals import contact_added, contact_removed

class CountryAdmin( admin.ModelAdmin ):
	list_display = ['name', 'iso_code', 'postal_zone', 'dialing_code', 'zip_after_city' ]
	list_editable = ['iso_code', 'postal_zone', 'dialing_code', 'zip_after_city' ]
	list_filter = ['groups', 'postal_zone', 'zip_after_city']
	search_fields = ['name', 'iso_code', 'dialing_code', ]
	filter_horizontal = ['groups']

class GroupCategoryAdmin( admin.ModelAdmin ):
	list_display = ['name', ]
	search_fields = ['name', ]
	
class PostalZoneAdmin( admin.ModelAdmin ):
	list_display = ['name', ]
	search_fields = ['name', ]

class FieldAdmin( admin.ModelAdmin ):
	list_display = ['name', ]
	search_fields = ['name', ]

class LabelAdmin( admin.ModelAdmin ):
	list_display = ['name', 'paper', 'repeat', 'enabled' ]
	search_fields = ['name', 'style', 'template' ]
	list_filter = [ 'enabled', 'paper' ]
	fieldsets = ( 
		( None, {
			'fields': ( ( 'name', 'repeat' , 'enabled' ), )
		} ),
		( 'Label template', {
			'fields': ( 'paper', 'style', 'template', )
		} ),
	)

class CountryGroupAdmin( admin.ModelAdmin ):
	list_display = ['id', 'name', 'category' ]
	list_editable = ['name', 'category' ]
	search_fields = ['name', 'category__name' ]
	list_filter = ['category', ]

class ContactGroupAdmin( admin.ModelAdmin ):
	list_display = ['id', 'name', 'category' ]
	list_editable = ['name', 'category' ]
	search_fields = ['name', 'category__name' ]
	list_filter = ['category', ]

class ContactFieldInlineAdmin( admin.TabularInline ):
	model = ContactField
	extra = 1

class ContactAdmin( AdminCommentMixin, admin.ModelAdmin ):
	list_display = ['id', 'title', 'last_name', 'first_name', 'organisation', 'department', 'street_1', 'street_2', 'city', 'country', 'email', 'phone', 'website', 'tags', 'created', 'last_modified' ]
	list_editable = ['title', 'first_name', 'last_name', 'email', 'organisation', 'department', 'street_1', 'street_2', 'city', 'phone', 'website', ]
	list_filter = ['last_modified', 'groups__category__name', 'groups', 'country__groups', 'extra_fields__name', 'country', 'title' ]
	search_fields = ['first_name', 'last_name', 'title', 'position', 'email', 'organisation', 'department', 'street_1', 'street_2', 'city', 'phone', 'website', 'social', ]
	fieldsets = ( 
		( None, {
			'fields': ( ( 'id', 'created', 'last_modified' ), )
		} ),
		( 'Person', {
			'fields': ( ( 'title', 'first_name', 'last_name' ), 'position', )
		} ),
		( 'Address', {
			'fields': ( 'organisation', 'department', 'street_1', 'street_2', 'city', 'country' )
		} ),
		( 'Groups', {
			'fields': ( 'groups', )
		} ),
		( 'Contact', {
			'fields': ( 'email', 'phone', 'website', 'social', )
		} ),
	)
	filter_horizontal = ['groups']
	readonly_fields = ['id', 'created', 'last_modified']
	inlines = [ ContactFieldInlineAdmin, AdminCommentInline, ]
	list_select_related = True
	
	def tags( self, obj ):
		return ", ".join( [unicode(x) for x in obj.groups.all()] )

	
	def get_urls( self ):
		urls = super( ContactAdmin, self ).get_urls()
		extra_urls = patterns( '',
			( r'^(?P<pk>[0-9]+)/label/$', self.admin_site.admin_view( self.label_view ) ),
		)
		return extra_urls + urls
	
	def label_view( self, request, pk=None ):
		"""
		Generate labels or show list of available labels
		"""
		# Get contact
		qs = Contact.objects.filter( pk=pk )
		if len(qs) == 0:
			raise Http404
		else:
			obj = qs[0]
		
		# Get label 
		try:
			label = Label.objects.get( pk=request.GET.get( 'label', None ), enabled=True )
			return label.get_label_render().render_http_response( qs, 'contact_label_%s.pdf' % obj.pk )
		except Label.DoesNotExist:
			# No label, so display list of available labels
			labels = Label.objects.filter( enabled=True ).order_by( 'name' )
			
			return render_to_response(
				"admin/contacts/contact/labels.html", 
				{
					'labels' : labels,
					'object' : obj,
					'messages': [],
					'app_label' : obj._meta.app_label,
					'opts' : obj._meta,
				}, 
				context_instance=RequestContext( request )
			)


	
	def action_make_label( self, request, queryset, label=None ):
		"""
		Action method for generating a PDF
		"""
		return label.get_label_render().render_http_response( queryset, 'contact_labels.pdf' )
	
	def action_set_group( self, request, queryset, group=None, remove=False ):
		"""
		Action method for set/removing groups to contacts.
		"""	
		for obj in queryset:
			if remove:
				obj.groups.remove( group )
			else:
				obj.groups.add( group )
				
	def save_model( self, request, obj, form, change ):
		"""
		Method needed to make Contact.m2m_changed_callback work correctly when saving
		in the admin. See notes for function and futher notes in signals.py.
		"""
		obj.save()
		obj.create_snapshot('save_model') # very important! trust me ;-)
	
	def response_change(self, request, obj, *args, **kwargs ):
		obj.dispatch_signals('save_model')
		return super(ContactAdmin, self).response_change(request, obj, *args, **kwargs)

	def response_add(self, request, obj, *args, **kwargs):
		obj.dispatch_signals('save_model')
		return super(ContactAdmin, self).response_add(request, obj, *args, **kwargs)		
			
	def _make_label_action( self, label ):
		"""
		Helper method to define an admin action for a specific label 
		"""
		name = 'make_label_%s' % label.pk
		action = lambda modeladmin, request, queryset: modeladmin.action_make_label( request, queryset, label=label )
		return ( name, ( action, name, "Make labels for selected objects (%s)" % label.name ) )
	
	def _make_group_action( self, group, remove=False ):
		"""
		Helper method to define an admin action for a specific group 
		"""
		name = 'unset_group_%s' % group.pk if remove else 'set_group_%s' % group.pk 
		action = lambda modeladmin, request, queryset: modeladmin.action_set_group( request, queryset, group=group, remove=remove )
		return ( name, ( action, name, "%s group %s" % ("Unset" if remove else "Set", group.name) ) )
	
	def get_actions( self, request ):
		"""
		Dynamically add admin actions for creating labels based on enabled labels.
		"""
		actions = super( ContactAdmin, self ).get_actions( request )
		actions.update( dict( [self._make_label_action( l ) for l in Label.objects.filter( enabled=True ).order_by( 'name' )] ) )
		actions.update( dict( [self._make_group_action( g, remove=False ) for g in ContactGroup.objects.all().order_by( 'name' )] ) )
		actions.update( dict( [self._make_group_action( g, remove=True ) for g in ContactGroup.objects.all().order_by( 'name' )] ) )
		return actions

class ContactGroupActionAdmin( admin.ModelAdmin ):
	list_display = ['group', 'on_event', 'action',  ]
	list_filter = [ 'on_event', 'action', 'group', ]
	search_fields = ['group__name', 'action__name', ]

def register_with_admin( admin_site ):
	admin_site.register( Label, LabelAdmin )
	admin_site.register( Field, FieldAdmin )
	admin_site.register( Country, CountryAdmin )
	admin_site.register( GroupCategory, GroupCategoryAdmin )
	admin_site.register( CountryGroup, CountryGroupAdmin )
	admin_site.register( ContactGroup, ContactGroupAdmin )
	admin_site.register( Contact, ContactAdmin )
	admin_site.register( PostalZone, PostalZoneAdmin )
	admin_site.register( ContactGroupAction, ContactGroupActionAdmin )
	

# Register with default admin site	
register_with_admin( admin.site )
