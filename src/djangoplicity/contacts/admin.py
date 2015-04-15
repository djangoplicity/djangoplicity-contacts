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

from django.conf.urls import patterns, url
from django.contrib import admin
from django.http import Http404
from django import forms
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import RequestContext
from djangoplicity.admincomments.admin import AdminCommentInline, \
	AdminCommentMixin
from djangoplicity.contacts.models import ContactGroup, Contact, Country, \
	CountryGroup, GroupCategory, ContactField, Field, Label, PostalZone, \
	ContactGroupAction, ImportTemplate, ImportMapping, ImportSelector, \
	ImportGroupMapping, Import, CONTACTS_FIELDS, ContactForm, Deduplication
from djangoplicity.contacts.tasks import import_data, contactgroup_change_check
from django.shortcuts import get_object_or_404

from collections import OrderedDict
from datetime import datetime


class ImportSelectorInlineAdmin( admin.TabularInline ):
	model = ImportSelector
	extra = 0


class ImportMappingForm( forms.ModelForm ):
	"""
	Form to dynamically set the field choices for an import mapping.
	"""
	field = forms.TypedChoiceField()

	def __init__( self, *args, **kwargs ):
		super( ImportMappingForm, self ).__init__( *args, **kwargs )
		self.fields['field'].choices = [( '', '---------' )] + CONTACTS_FIELDS + Field.field_options()

	class Meta:
		model = ImportMapping


class ImportMappingInlineAdmin( admin.TabularInline ):
	model = ImportMapping
	form = ImportMappingForm
	extra = 0


class ImportGroupMappingInlineAdmin( admin.TabularInline ):
	model = ImportGroupMapping
	extra = 0


class ImportAdmin( admin.ModelAdmin ):
	list_display = [ 'template', 'last_modified', 'created' ]
	list_filter = [ 'last_modified', 'created' ]
	readonly_fields = ['status', 'last_modified', 'created' ]
	fieldsets = (
		( None, {
			'fields': ( 'template', 'data_file', )
		} ),
		( 'Status', {
			'fields': ( 'status', 'last_modified', 'created' )
		} ),
	)

	def get_urls( self ):
		urls = super( ImportAdmin, self ).get_urls()
		extra_urls = patterns( '',
				url( r'^(?P<pk>[0-9]+)/preview/$', self.admin_site.admin_view( self.preview_view ), name='contacts_import_preview' ),
			url( r'^(?P<pk>[0-9]+)/import/$', self.admin_site.admin_view( self.import_view ), name='contacts_import' ),
			url( r'^(?P<pk>[0-9]+)/review/$', self.admin_site.admin_view( self.review_view ), name='contacts_import_review' ),
		)
		return extra_urls + urls

	def preview_view( self, request, pk=None ):
		"""
		Show preview of imports based on template
		"""
		obj = get_object_or_404( Import, pk=pk )

		try:
			mapping, rows = obj.preview_data()
			return render_to_response(
				"admin/contacts/import/preview.html",
				{
					'columns': mapping,
					'rows': rows,
					'object': obj,
					'messages': [],
					'app_label': obj._meta.app_label,
					'opts': obj._meta,
				},
				context_instance=RequestContext( request )
			)
		except Exception, e:
			return render_to_response(
				"admin/contacts/import/preview.html",
				{
					'error': e.message,
					'object': obj,
					'messages': [],
					'app_label': obj._meta.app_label,
					'opts': obj._meta,
				},
				context_instance=RequestContext( request )
			)

	@classmethod
	def clean_import_data(cls, request_POST):
		'''
		Clean the POST data to be used by import_data
		Returns: dict of dicts:
		{'line_number ': {
			'target: 'new' or 'id'	# Create new contact or update 'id'
			'form': {}				# ContactForm for the given contact
		}, }
		'''
		contacts = {}
		# Identify which entries need to be imported:
		for key in request_POST:
			if not key.startswith('_selected_import_'):
				continue

			if request_POST.get(key) != 'on':
				# This should never happen...
				continue

			import_id = key.split('_selected_import_')[1]

			# Identify if a new contact should be created or an existing one updated:
			contacts[import_id] = {
				'target': request_POST.get('_selected_merge_contact_%s' % import_id),
				'post': request_POST.copy(),
				# Make a copy of post data so we can handle each entry separately
			}

		for contact in contacts:
			target = contacts[contact]['target']
			if not target:
				contacts[contact]['form'] = None
				continue

			# Generate prefix to be used in form:
			prefix = '%s_%s' % (contact, target)

			# Remove data from other contacts from the post data:
			keys_to_delete = []
			for key in contacts[contact]['post']:
				if not key.startswith(prefix):
					keys_to_delete.append(key)
			for key in keys_to_delete:
				del contacts[contact]['post'][key]

			# Fetch the existing contact if updating:
			if target != 'new':
				original_contact = Contact.objects.get(id=target.split('_')[1])
				form = ContactForm(contacts[contact]['post'],
									instance=original_contact,
									prefix=prefix)
			else:
				form = ContactForm(contacts[contact]['post'], prefix=prefix)

			contacts[contact]['form'] = form

		return contacts

	def import_view( self, request, pk=None ):
		"""
		Import the data in the DB
		"""
		obj = get_object_or_404( Import, pk=pk )

		# Import in background
		if request.method == "POST":

			import_contacts = self.clean_import_data(request.POST)

			# Check that all the forms are valid, if not create
			# a list of error messages
			errorlist = []
			for line, contact in import_contacts.iteritems():
				if not contact['form']:
					continue
				if not contact['form'].is_valid():
					# Convert the ErrorList to a dict including the field value for the template:
					errors = []
					for field, error in contact['form']._errors.iteritems():
						errors.append({
							'field': field,
							'error': error,
							'value': contact['form'][field].value,
						})

					errorlist.append({
						'line': line,
						'errors': errors,
						'value': contact['form']
					})

			if not errorlist:
				# request.POST is a QueryDict, and it can't be serialized easily
				# so we convert it to a dict. All the values are single values
				# except for the groups so we look at the key name to figure out
				# how to extract the values from the QueryDict
				d = {}
				for key in request.POST:
					if key.endswith('-groups'):
						d[key] = request.POST.getlist(key)
					else:
						d[key] = request.POST[key]
				import_data.delay( obj.pk, d )

			return render_to_response(
					"admin/contacts/import/import.html",
					{
						'object': obj,
						'errorlist': errorlist,
						'messages': [],
						'app_label': obj._meta.app_label,
						'opts': obj._meta,
					},
					context_instance=RequestContext( request )
				)
		else:
			raise Http404

	def review_view( self, request, pk=None ):
		"""
		Run a duplicate detection tasks in the background
		"""
		obj = get_object_or_404( Import, pk=pk )

		# Prepare the smart import in the background
		if not obj.last_deduplication or request.method == "POST":
			if obj.status != 'processing':
				obj.status = 'processing'
				obj.last_deduplication = datetime.now()
				obj.save()

			from djangoplicity.contacts.tasks import prepare_import
			prepare_import.delay( obj.pk, request.user.email )

		mapping, imported, new, duplicates = obj.review_data()

		return render_to_response(
				"admin/contacts/import/review.html",
				{
					'columns': mapping,
					'imported': imported,
					'new': new,
					'duplicates': duplicates,
					'object': obj,
					'messages': [],
					'app_label': obj._meta.app_label,
					'opts': obj._meta,
				},
				context_instance=RequestContext( request )
			)


class ImportTemplateAdmin( admin.ModelAdmin ):
	list_display = ['name', 'duplicate_handling', 'tag_import', ]
	list_editable = ['duplicate_handling', 'tag_import', ]
	search_fields = ['name', ]
	filter_horizontal = ['extra_groups', 'frozen_groups']
	fieldsets = (
		( None, {
			'fields': ( 'name', 'tag_import', 'extra_groups' )
		} ),
		( 'Duplicate handling', {
			'fields': ( 'duplicate_handling', 'frozen_groups' )
		} ),
	)
	inlines = [ImportSelectorInlineAdmin, ImportMappingInlineAdmin]


class ImportMappingAdmin( admin.ModelAdmin ):
	list_display = ['template', 'header', 'group_separator', ]
	list_editable = ['header', 'group_separator', ]
	search_fields = ['header', 'field', 'group_separator', ]
	readonly_fields = ['template']
	fieldsets = (
		( None, {
			'fields': ( 'template', 'header', 'group_separator' )
		} ),
	)
	inlines = [ImportGroupMappingInlineAdmin]

	def queryset( self, request ):
		qs = super( ImportMappingAdmin, self ).queryset( request )
		qs = qs.filter( field='groups' )
		return qs


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
	list_display = ['slug', 'name', 'blank' ]
	search_fields = ['slug', 'name', ]


class LabelAdmin( admin.ModelAdmin ):
	list_display = ['name', 'paper', 'repeat', 'enabled' ]
	search_fields = ['name', 'style', 'template' ]
	list_filter = [ 'enabled', 'paper' ]
	fieldsets = (
		( None, {
			'fields': ( ( 'name', 'repeat', 'enabled' ), )
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
	list_display = ['id', 'name', 'category', 'order' ]
	list_editable = ['name', 'category', 'order' ]
	search_fields = ['name', 'category__name' ]
	list_filter = ['category', ]
	ordering = ['name', ]

	def queryset(self, request):
		return super(ContactGroupAdmin, self).queryset(request).select_related('category')

	def formfield_for_dbfield(self, db_field, **kwargs):
		'''
		Cache the category choices to speed up admin list view
		'''
		request = kwargs['request']
		formfield = super(ContactGroupAdmin, self).formfield_for_dbfield(db_field, **kwargs)
		if db_field.name in ('category', ):
			choices_cache = getattr(request, '%s_choices_cache' % db_field.name, None)
			if choices_cache is not None:
				formfield.choices = choices_cache
			else:
				setattr(request, '%s_choices_cache' % db_field.name, formfield.choices)
		return formfield


class ContactFieldInlineAdmin( admin.TabularInline ):
	model = ContactField
	extra = 1


class ContactAdmin( AdminCommentMixin, admin.ModelAdmin ):
	list_display = ['id', 'title', 'last_name', 'first_name', 'position', 'organisation', 'department', 'tags', 'group_order', 'street_1', 'street_2', 'city', 'country', 'language', 'email', 'phone', 'website', 'created', 'last_modified' ]
	list_editable = ['title', 'first_name', 'last_name', 'position', 'email', 'organisation', 'department', 'street_1', 'street_2', 'city', 'phone', 'website', 'language', ]
	list_filter = ['last_modified', 'groups__category__name', 'groups', 'country__groups', 'extra_fields__name', 'country', 'language', 'title' ]
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
			'fields': ( 'email', 'phone', 'website', 'social', 'language' )
		} ),
	)
	filter_horizontal = ['groups']
	readonly_fields = ['id', 'created', 'last_modified']
	inlines = [ ContactFieldInlineAdmin, AdminCommentInline, ]
	list_select_related = True

	def queryset(self, request):
		return super(ContactAdmin, self).queryset(request).select_related('country').prefetch_related('groups')

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
					'labels': labels,
					'object': obj,
					'messages': [],
					'app_label': obj._meta.app_label,
					'opts': obj._meta,
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
			contactgroup_change_check.apply_async(
				(list(obj.groups.values_list('id', flat=True)), obj.id),
				countdown=20,
			)
			if remove:
				obj.groups.remove( group )
			else:
				obj.groups.add( group )

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
		actions.update( OrderedDict( [self._make_label_action( l ) for l in Label.objects.filter( enabled=True ).order_by( 'name' )] ) )
		actions.update( OrderedDict( [self._make_group_action( g, remove=False ) for g in ContactGroup.objects.all().order_by( 'name' )] ) )
		actions.update( OrderedDict( [self._make_group_action( g, remove=True ) for g in ContactGroup.objects.all().order_by( 'name' )] ) )

		return actions

	class Media:
		# Javascript to collapse filter pane in admin
		js = ['djangoplicity/js/list_filter_collapse.js']


class ContactGroupActionAdmin( admin.ModelAdmin ):
	list_display = ('group', 'on_event', 'action', )
	list_filter = ('on_event', 'action', 'group', )
	search_fields = ('group__name', 'action__name', )


class DeduplicationAdmin(admin.ModelAdmin):
	list_display = ('id', 'last_deduplication', )
	exclude = ('last_deduplication', )
	readonly_fields = ('status', 'duplicate_contacts', 'deduplicated_contacts', )
	filter_horizontal = ('groups', )

	def get_urls(self):
		urls = super(DeduplicationAdmin, self).get_urls()
		extra_urls = patterns('',
			url(r'^(?P<pk>[0-9]+)/run/$', self.admin_site.admin_view(self.run), name='contacts_deduplication_run'),
			url(r'^(?P<pk>[0-9]+)/review/page/(?P<page>[0-9]+)/$', self.admin_site.admin_view(self.review_view), name='contacts_deduplication_review_page'),
			url(r'^(?P<pk>[0-9]+)/review/$', self.admin_site.admin_view(self.review_view), name='contacts_deduplication_review'),
		)
		return extra_urls + urls

	def run(self, request, pk=None):
		'''
		Run deduplication tasks for given groups
		'''

		dedup = get_object_or_404(Deduplication, pk=pk)

		# Run the deduplication in the background
		if dedup.status != 'processing':
			dedup.status = 'processing'
			dedup.last_deduplication = datetime.now()
			dedup.save()

			from djangoplicity.contacts.tasks import run_deduplication
			run_deduplication.delay(dedup.pk, request.user.email)

		return redirect('admin:contacts_deduplication_review', pk=dedup.pk)

	def review_view(self, request, pk=None, page=1):
		page = int(page)
		if request.method == "POST":
			return self.deduplicate_view(request, pk)

		dedup = get_object_or_404(Deduplication, pk=pk)

		duplicates, total_duplicates = dedup.review_data(page)

		return render_to_response(
			"admin/contacts/deduplication/review.html",
			{
				'object': dedup,
				'messages': [],
				'app_label': dedup._meta.app_label,
				'opts': dedup._meta,
				'duplicates': duplicates,
				'total_duplicates': total_duplicates,
				'page': page,
				'pages': range(1, (total_duplicates / dedup.max_display + 2)),
			},
			context_instance=RequestContext(request)
		)

	def deduplicate_view(self, request, pk=None):
		dedup = get_object_or_404(Deduplication, pk=pk)

		update, delete, ignore = self._clean_deduplicate_data(request)

		# Check that all the update forms are valid, if not create
		# a list of error messages
		errorlist = []
		for dummy, contact in update.iteritems():
			if not contact['form'].is_valid():
				# Convert the ErrorList to a dict including the field value for the template:
				errors = []
				for field, error in contact['form']._errors.iteritems():
					errors.append({
						'field': field,
						'error': error,
						'value': contact['form'][field].value,
					})

				errorlist.append({
					'contact': contact['contact'],
					'errors': errors,
					'value': contact['form']
				})

		resultlist = []
		if not errorlist:
			resultlist = dedup.deduplicate_data(update, delete, ignore)

		return render_to_response(
				"admin/contacts/deduplication/deduplicate.html",
				{
					'object': dedup,
					'errorlist': errorlist,
					'resultlist': resultlist,
					'messages': [],
					'app_label': dedup._meta.app_label,
					'opts': dedup._meta,
				},
				context_instance=RequestContext( request )
			)

	def _clean_deduplicate_data(self, request):
		'''
		Clean the POST data to be used by deduplicate_view
		'''
		update = {}
		delete = []
		ignore = []

		for key in request.POST:
			if not key.startswith('action_contact_'):
				continue

			# The key will of the form action_contact_22400_22400 or
			# action_contact_22400_29985, for the "original" contact
			# and for a potential duplicate
			target = key[len('action_contact_'):]

			action = request.POST.get(key)

			if action == 'delete':
				delete.append(target)
				continue
			if action == 'ignore':
				ignore.append(target)
				continue

			# If we reach this point then action == 'update'

			# Make a copy of post data so we can handle each
			# entry separately
			update[target] = {'post': request.POST.copy()}

		for target in update:
			# Remove data from other contacts from the post data:
			keys_to_delete = []
			for key in update[target]['post']:
				if not key.startswith(target):
					keys_to_delete.append(key)
			for key in keys_to_delete:
				del update[target]['post'][key]

			original_contact = Contact.objects.get(id=target.split('_')[1])
			form = ContactForm(update[target]['post'],
								instance=original_contact,
								prefix=target)

			update[target]['contact'] = original_contact
			update[target]['form'] = form

		return update, delete, ignore


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
	admin_site.register( ImportTemplate, ImportTemplateAdmin )
	admin_site.register( ImportMapping, ImportMappingAdmin )
	admin_site.register( Import, ImportAdmin )
	admin_site.register( Deduplication, DeduplicationAdmin )


# Register with default admin site
register_with_admin( admin.site )
