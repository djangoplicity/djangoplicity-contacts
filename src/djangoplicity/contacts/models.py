# -*- coding: utf-8 -*-
#
# djangoplicity-contacts
# Copyright (c) 2007-2011, European Southern Observatory (ESO)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#	* Redistributions of source code must retain the above copyright
#	  notice, this list of conditions and the following disclaimer.
#
#	* Redistributions in binary form must reproduce the above copyright
#	  notice, this list of conditions and the following disclaimer in the
#	  documentation and/or other materials provided with the distribution.
#
#	* Neither the name of the European Southern Observatory nor the names 
#	  of its contributors may be used to endorse or promote products derived
#	  from this software without specific prior written permission.
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


from datetime import datetime
from dirtyfields import DirtyFieldsMixin
from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models.signals import m2m_changed, pre_delete, post_delete, \
	post_save, pre_save
from django.forms import ValidationError
from django.template import loader, Context, Template
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _
from djangoplicity.actions.models import Action
from djangoplicity.contacts.labels import LabelRender, LABEL_PAPER_CHOICES
from djangoplicity.contacts.signals import contact_added, contact_removed, \
	contact_updated
import logging
import os


logger = logging.getLogger( 'djangoplicity' )

class Label( models.Model ):
	"""
	Object to define labels
	"""
	name = models.CharField( max_length=255 )
	paper = models.CharField( max_length=255, choices=LABEL_PAPER_CHOICES )
	repeat = models.PositiveIntegerField( default=1 )
	style = models.TextField( blank=True )
	template = models.TextField( blank=True )
	enabled = models.BooleanField( default=True )

	def get_label_render( self ):
		return LabelRender( self.paper, label_template=self.template, style=self.style, repeat=self.repeat )

	class Meta:
		ordering = ['name']


class Field( models.Model ):
	name = models.CharField( max_length=255, unique=True )
	blank = models.BooleanField( default=True )

	def __unicode__( self ):
		return self.name

	class Meta:
		ordering = ['name']

class GroupCategory( models.Model ):
	"""
	Groupings of groups.
	"""
	name = models.CharField( max_length=255, blank=True )

	def __unicode__( self ):
		return self.name

	class Meta:
		verbose_name_plural = 'group categories'
		ordering = ( 'name', )


class CountryGroup( models.Model ):
	"""
	Allow grouping of countries (e.g. EU, member states, postal zones)
	"""
	name = models.CharField( max_length=255, blank=True, db_index=True )
	category = models.ForeignKey( GroupCategory, blank=True, null=True )

	def __unicode__( self ):
		return self.name

	class Meta:
		ordering = ( 'category__name', 'name' )

class PostalZone( models.Model ):
	"""
	Postal zones for countries
	"""
	name = models.CharField( max_length=255, unique=True )

	def __unicode__( self ):
		return self.name

	class Meta:
		ordering = [ 'name', ]


class Country( models.Model ):
	"""
	Country model for storing country names.
	"""
	name = models.CharField( max_length=40, db_index=True )
	iso_code = models.CharField( _( 'ISO code' ), max_length=5, blank=True )
	dialing_code = models.CharField( max_length=10, blank=True )
	zip_after_city = models.BooleanField( default=False )
	postal_zone = models.ForeignKey( PostalZone, null=True, blank=True )
	groups = models.ManyToManyField( CountryGroup, blank=True )

	def get_zip_city( self, zip, city ):
		"""
		Method to combine ZIP/post case and city for a country.
		"""
		if self.zip_after_city:
			return ( "%s %s" % ( city, zip ) ).strip()
		else:
			return ( "%s %s" % ( zip, city ) ).strip()

	@classmethod
	def country_index( cls ):
		"""
		Get a dictionary which can be indexed by ISO code to get the country.
		"""
		data = {}
		for c in cls.objects.all():
			if c.iso_code:
				data[c.iso_code.upper()] = c
		return data

	def save( self, *args, **kwargs ):
		""" Ensure ISO code is in upper case """
		self.iso_code = self.iso_code.upper()
		super( Country, self ).save( *args, **kwargs )

	def __unicode__( self ):
		return self.name

	class Meta:
		verbose_name_plural = _( 'countries' )
		ordering = ['name', ]


class ContactGroup( DirtyFieldsMixin, models.Model ):
	"""
	Groups for contacts
	
	The order field allows to specify a numerical values
	by which the groups should be sorted and allows you to 
	sort contacts by the ordering of groups. Due to the way the django
	ORM works, it's however difficult to order by a related attribute
	and at the same time select only distinct contacts. For that reason
	a minimum group order value is stored on each contact. This value
	is automatically propagated to all contacts.
	
	djangoplicity.contacts.tets.orderpropagation contains tests to validate
	that the propagation happens correctly.    
	"""
	name = models.CharField( max_length=255, blank=True )
	category = models.ForeignKey( GroupCategory, blank=True, null=True )
	order = models.PositiveIntegerField( blank=True, null=True )
	
	def get_emails( self ):
		""" Get all email addresses for contacts in this group """
		return self.contact_set.exclude( email='' ).values_list( 'email', flat=True )

	def __unicode__( self ):
		return self.name
	
	@classmethod
	def pre_delete_callback( cls, sender, instance=None, **kwargs ):
		"""
		"""
		logger.debug( "%s.pre_delete" % cls.__name__ )
		
		# Get a query of contacts to update and make sure it's evaluated
		if instance.order:
			instance._cached_contact_set = list( instance.contact_set.filter( group_order__gte=instance.order ).values_list( 'pk', flat=True ) )
		else:
			instance._cached_contact_set = []
				
	@classmethod
	def post_delete_callback( cls, sender, instance=None, **kwargs ):
		"""
		"""
		logger.debug( "%s.post_delete" % cls.__name__ )
		
		for c in Contact.objects.filter( pk__in=instance._cached_contact_set ).annotate( min__group_order=models.Min( 'groups__order' ) ):
			if c.group_order != c.min__group_order:
				Contact.objects.filter( pk=c.pk ).update( group_order=c.min__group_order )
		
	@classmethod
	def pre_save_callback( cls, sender, instance=None, raw=False, **kwargs ):
		"""
		"""
		logger.debug( "%s.pre_save" % cls.__name__ )
		instance._dirty_fields = instance.get_dirty_fields()

	@classmethod
	def post_save_callback( cls, sender, instance=None, raw=False, **kwargs ):
		"""
		"""
		logger.debug( "%s.post_save" % cls.__name__ )
		
		dirty_fields = instance._dirty_fields
		instance._dirty_fields = None
		
		if 'order' in dirty_fields:
			if dirty_fields['order'] is None or dirty_fields['order'] - instance.order > 0:
				# Order value was changed to a smaller value - hence we must update all contacts
				# with a group_order greater than instance.order.
				instance.contact_set.filter( group_order__gt=instance.order ).update( group_order=instance.order )
			elif instance.order is None or dirty_fields['order'] - instance.order < 0:
				# Order value was changed to a greater value - hence we must update all contacts
				# with a group_order greater than the *old* instance.order
				for c in Contact.objects.filter( pk__in=instance.contact_set.filter( group_order__gte=dirty_fields['order'] ) ).annotate( min__group_order=models.Min( 'groups__order' ) ):
					if c.group_order != c.min__group_order:
						Contact.objects.filter( pk=c.pk ).update( group_order=c.min__group_order )
		
		# Reset dirty state - DirtyFieldMixin is supposed to do it automatically,
		# but apparently there's some conflicts with the signals it seems like.
		instance._original_state = instance._as_dict()
											
	class Meta:
		ordering = ( 'order', 'name', )

class Contact( DirtyFieldsMixin, models.Model ):
	"""
	Contacts model
	"""
	first_name = models.CharField( max_length=255, blank=True )
	last_name = models.CharField( max_length=255, blank=True )
	title = models.CharField( max_length=50, blank=True, db_index=True )
	position = models.CharField( max_length=255, blank=True )
	organisation = models.CharField( max_length=255, blank=True )
	department = models.CharField( max_length=255, blank=True )
	street_1 = models.CharField( max_length=255, blank=True )
	street_2 = models.CharField( max_length=255, blank=True )
	city = models.CharField( max_length=255, blank=True )
	country = models.ForeignKey( Country, blank=True, null=True )

	phone = models.CharField( max_length=255, blank=True )
	website = models.CharField( 'Website', max_length=255, blank=True )
	social = models.CharField( 'Social media', max_length=255, blank=True )
	email = models.EmailField( blank=True )

	groups = models.ManyToManyField( ContactGroup, blank=True )
	group_order = models.PositiveIntegerField( blank=True, null=True ) #
	
	extra_fields = models.ManyToManyField( Field, through='ContactField' )

	created = models.DateTimeField( auto_now_add=True )
	last_modified = models.DateTimeField( auto_now=True )

	def create_snapshot( self, action=None ):
		"""
		Take a snapshot of the groups for this contact. The snapshot 
		is used to detect added/removed groups.
		"""
		if not hasattr( self, '_snapshot' ):
			self._snapshot = None

		logger.debug( "create_snapshot:%s" % action )
		if self._snapshot is None:
			self._snapshot = ( action, set( self.groups.all() ) )


	def get_snapshot( self, action ):
		"""
		Get the snapshot. Returns None if no snapshot was taken.
		"""
		if self._snapshot is not None:
			if self._snapshot[0] is None or self._snapshot[0] == action:
				return self._snapshot[1]
		return None

	def reset_snapshot( self ):
		"""
		Reset the current snapshot.
		"""
		self._snapshot = None

	def set_extra_field( self, field_name, value ):
		"""
		Convenience method to set the value of an extra field on a contact
		"""
		f = Field.objects.get( name=field_name )
		try:
			cf = ContactField.objects.get( field=f, contact=self )
		except ContactField.DoesNotExist:
			cf = ContactField( field=f, contact=self )

		cf.value = value
		cf.save()


	def get_extra_field( self, field_name ):
		"""
		Convenience method to get the value of an extra field on a contact
		"""
		f = Field.objects.get( name=field_name )
		try:
			cf = ContactField.objects.get( field=f, contact=self )
			return cf.value
		except ContactField.DoesNotExist:
			return None

	def get_data( self ):
		"""
		Get a dictionary of this object
		"""
		data = {}
		data['name'] = ( "%s %s %s" % ( self.title, self.first_name, self.last_name ) ).strip()
		data['address_lines'] = [x.strip() for x in self.organisation, self.department, self.street_1, self.street_2]
		data['city'] = self.city.strip()
		data['email'] = self.email.strip()
		data['country'] = self.country.iso_code.upper() if self.country else ''
		data['contact_object'] = self
		return data

	ALLOWED_FIELDS = ['first_name', 'last_name', 'title', 'position', 'organisation', 'department', 'street_1', 'street_2', 'city', 'zip', 'state', 'country', 'phone', 'website', 'social', 'email',]

	@classmethod
	def find_or_create_object( cls, **kwargs ):
		"""
		Find an object or create it if no match was found.
		"""
		obj = cls.find_object( **kwargs )
		return obj if obj else cls.create_object( **kwargs )

	@classmethod
	def _select_contact( cls, qs ):
		"""
		"""
		qsnew = filter( lambda x: 'librarian' in x.last_name.lower(), qs )
		if len(qsnew) > 0:
			return qsnew[0]
		else:
			return qs[0]
	
	@classmethod
	def find_objects( cls, **kwargs ):
		"""
		Find all matching contacts
		"""
		for field in ['email']:
			if field in kwargs and kwargs[field]:
				qs = cls.objects.filter( email=kwargs[field] )
				if len( qs ) >= 1:
					return qs
		return None
			
	@classmethod
	def find_object( cls, **kwargs ):
		"""
		Find one matching contact
		"""
		qs = cls.find_objects( **kwargs )
		if qs: 
			if len( qs ) == 1:
				return qs[0]
			elif len( qs ) > 1:
				return cls._select_contact( qs )
		return None
		
		
	@classmethod
	def create_object( cls, groups=[], **kwargs ):
		"""
		Create a new contact from dictionary.
		"""
		obj = cls()
		if obj.update_object( **kwargs ):
			obj.save()
			if groups:
				obj.groups.add( *ContactGroup.objects.filter( name__in=groups ) )
			return obj
		else:
			return None

	def update_object( self, **kwargs ):
		"""
		Update a contact with new information from a dictionary. Following keys are supported:
		  * first_name
		  * last_name
		  * title
		  * position
		  * organisation
		  * department
		  * street_1
		  * street_2
		  * city 
		  * zip, postal_code, state, city - since the contacts only have a city field, these will be concatenated, also country must be set 
		  * country (2 letter ISO code)
		  * phone
		  * website
		  * social
		  * email
		"""
		changed = False
		
		ctry = None
		if 'country' in kwargs:
			if kwargs['country'] and len( kwargs['country'] ) == 2:
				ctry = Country.objects.get( iso_code=kwargs['country'].upper() )
			elif kwargs['country']:
				ctry = Country.objects.get( name__ieq=kwargs['country'] )
			self.country = ctry
			changed = True
			del kwargs['country']
		
		if ctry:
			
			zip_code = kwargs.get( 'zip', None )
			postal_code = kwargs.get( 'postal_code', None )
			state = kwargs.get( 'state', None )
			city = kwargs.get( 'city', None )
			
			if zip_code or postal_code or state or city:
				if ctry.zip_after_city:
					self.city = "  ".join( filter( lambda x: x, [city, state, zip_code, postal_code, ] ) )
				else:
					self.city = "  ".join( filter( lambda x: x, [zip_code, postal_code, city, state] ) )
				changed = True
		elif 'city' in kwargs:
			self.city = kwargs['city']
			changed = True
			
		# Delete keys that have already been dealt with.	
		for k in ['zip', 'postal_code', 'state', 'city']:
			if k in kwargs:
				del kwargs[k]
		
		# The rest is simply settings the fields
		for field, val in kwargs.items():
			if field in self.ALLOWED_FIELDS:
				setattr( self, field, val )
				changed = True
		
		return changed



	def __unicode__( self ):
		if self.first_name or self.last_name:
			return ( "%s %s %s" % ( self.title, self.first_name, self.last_name ) ).strip()
		elif self.organisation:
			return self.organisation
		elif self.department:
			return self.department
		else:
			return unicode( self.pk )

	def dispatch_signals( self, action ):
		old_groups = self.get_snapshot( action )
		# Signals only sent if snapshot was created with the same action
		if old_groups is not None:
			logger.debug( "dispatch_signals:%s" % action )
			new_groups = set( self.groups.all() )
			# added groups
			for g in new_groups - old_groups:
				logger.debug( "send contact_added" )
				contact_added.send( sender=self.__class__, group=g, contact=self )

			# removed groups
			for g in old_groups - new_groups:
				logger.debug( "send contact_removed" )
				contact_removed.send( sender=self.__class__, group=g, contact=self )


			self.reset_snapshot()

	@classmethod
	def m2m_changed_callback( cls, sender, instance=None, action=None, reverse=None, model=None, pk_set=[], **kwargs ):
		"""
		m2m_changed signal callback handler. Note, due to strange implementation of
		c.groups = [...] feature (used by admin) it's overly complex to figure out
		which groups was added/removed for a contact.
		
		Callback is used to send contact_removed, contact_added signals
		
		TODO: Does not take the reverse relation into account - e.g: grp.contact_set.add(..)
		TODO: When last group is removed via admin, only a pre_clear, post_clear is sent, and not a pre_clear, post_clear, pre_add, post_add  
		"""
		logger.debug( "%s.m2m_changed:%s" % ( cls.__name__, action ) )
		
		# Pre-compute group ordering
		if action in ['post_add', 'post_remove']:
			try:
				min_order = instance.groups.all().aggregate( min_order=models.Min( 'order' ) )['min_order']
				if min_order != instance.group_order:
					cls.objects.filter( pk=instance.pk ).update( group_order=min_order )
					instance.group_order = min_order
			except KeyError:
				if min_order is not None:
					cls.objects.filter( pk=instance.pk ).update( group_order=None )
					instance.group_order = None
		if action == 'post_clear':
			if instance.group_order is not None: 
				cls.objects.filter( pk=instance.pk ).update( group_order=None )
				instance.group_order = None

		if action in ['pre_clear', 'pre_remove', 'pre_add']:
			instance.create_snapshot( action[4:] )
		elif action in ['post_clear', 'post_remove', 'post_add']:
			instance.dispatch_signals( action[5:] )
			


	@classmethod
	def pre_delete_callback( cls, sender, instance=None, **kwargs ):
		"""
		Callback is used to send contact_removed, contact_added signals
		"""
		logger.debug( "%s.pre_delete" % cls.__name__ )
		for g in instance.groups.all():
			contact_removed.send_robust( sender=cls, group=g, contact=instance )

	@classmethod
	def pre_save_callback( cls, sender, instance=None, raw=False, **kwargs ):
		"""
		Callback for detecting changes to the model.
		"""
		logger.debug( "%s.pre_save" % cls.__name__ )
		if instance.email:
			# All email addresses use lower-case
			instance.email = instance.email.lower()
		instance._dirty_fields = instance.get_dirty_fields()

	@classmethod
	def post_save_callback( cls, sender, instance=None, raw=False, **kwargs ):
		"""
		Callback for detecting changes to the model.
		"""
		logger.debug( "%s.post_save" % cls.__name__ )
		
		dirty_fields = instance._dirty_fields
		instance._dirty_fields = None
		if dirty_fields != {}:
			logger.debug( "send contact_updated" )
			contact_updated.send( sender=cls, instance=instance, dirty_fields=dirty_fields )


	class Meta:
		ordering = ['last_name']


class ContactField( models.Model ):
	"""
	Stores a field value for a given contact.
	"""
	field = models.ForeignKey( Field )
	contact = models.ForeignKey( Contact )
	value = models.CharField( max_length=255, blank=True, db_index=True )

	def __unicode__( self ):
		return self.value 

	def full_clean( self, exclude=None ):
		super( ContactField, self ).full_clean( exclude=exclude )
		# Apparently if field is null (i.e. not set in admin), it's not detected
		# until validate_unique, so we check it as the last step. 
		if self.field.blank and self.value == '':
			raise ValidationError( "Field %s does not allow blank values" % self.field )

	class Meta:
		unique_together = ( 'field', 'contact' )

#
# More advanced stuff - configurable actions to be execute once
# contacts are added/removed from groups (e.g subscribe to mailman).
#
ACTION_EVENTS = ( 
	( 'contact_added', 'Contact added to group' ),
	( 'contact_removed', 'Contact removed from group' ),
	( 'contact_updated', 'Contact updated' ),
	( 'periodic_5min', 'Every 5 minutes' ),
	( 'periodic_30min', 'Every 30 minutes' ),
	( 'periodic_1hr', 'Every hour' ),
	( 'periodic_6hr', 'Every 6 hours' ),
	( 'periodic_24hr', 'Every day' ),
 )

class ContactGroupAction( models.Model ):
	"""
	Define actions to be executed when a contact is added
	or removed to a group.
	"""
	group = models.ForeignKey( ContactGroup )
	action = models.ForeignKey( Action )
	on_event = models.CharField( max_length=50, choices=ACTION_EVENTS, db_index=True )

	_key = 'djangoplicity.contacts.action_cache'

	@classmethod
	def clear_cache( cls, *args, **kwargs ):
		"""
		Ensure cache is reset in case any change is made.
		"""
		logger.debug( "clearing action cache" )
		cache.delete( cls._key )

	@classmethod
	def create_cache( cls, *args, **kwargs ):
		"""
		Generate new action cache.
		
		The cache has two ways of indexing:
			* by group then event
			* or, event then group
			
		Since ``group_pk'' are always numbers, and ``on_event'' is 
		always characters, the keys will not collide. 
		
		cache = {
			'<group_pk>' : {
				'<on_event>' : [ <action>, ... ],
				...
			},
			...
			'<on_event>' : {
				'<group_pk>' : [ <action>, ... ],
				'<group_pk>' : [ <action>, ... ],
			}, 
			...
		}
		"""
		logger.debug( "generating action cache" )
		action_cache = {}
		for a in cls.objects.all().select_related( depth=1 ).order_by( 'group', 'on_event', 'action' ):
			g_pk = str( a.group.pk )
			# by group_pk, event
			if g_pk not in action_cache:
				action_cache[ g_pk ] = {}
			if a.on_event not in action_cache[g_pk]:
				action_cache[ g_pk ][a.on_event] = []

			if a.on_event not in action_cache:
				action_cache[a.on_event] = {}
			if g_pk not in action_cache[a.on_event]:
				action_cache[a.on_event][ g_pk ] = []

			action_cache[ g_pk ][a.on_event].append( a.action )
			action_cache[ a.on_event ][g_pk].append( a.action )

			# by event, group_pk = actions

		cache.set( cls._key, action_cache )
		return action_cache

	@classmethod
	def get_cache( cls, ):
		"""
		Get the action cache - generate it if necessary.
		
		Caches results to prevent many queries to the database. Currently the entire
		table is cached, however in case of issues, this caching strategy can be improved.
		"""
		action_cache = cache.get( cls._key )

		# Prime cache if needed
		if action_cache is None:
			action_cache = cls.create_cache()

		return action_cache

	@classmethod
	def get_actions_for_event( cls, on_event, group_pk=None ):
		"""
		"""
		action_cache = cls.get_cache()

		try:
			actions = action_cache[on_event]
			return actions if group_pk is None else actions[str( group_pk )]
		except:
			return {} if group_pk is None else []


	@classmethod
	def get_actions( cls, group, on_event=None ):
		"""
		Get all actions defined for a certain group.
		"""
		action_cache = cls.get_cache()

		# Find actions for this group 
		try:
			actions = action_cache[ str( group.pk ) ]
			return actions if on_event is None else actions[on_event]
		except KeyError:
			return {} if on_event is None else []


	@classmethod
	def contact_added_callback( cls, sender=None, group=None, contact=None, **kwargs ):
		"""
		Callback handler for when a contact is *added* to a group. Will execute defined
		actions for this group.
		"""
		logger.debug( "contact %s added to group %s" % ( contact.pk, group.pk ) )
		for a in cls.get_actions( group, on_event='contact_added' ):
			a.dispatch( group=group, contact=contact )

	@classmethod
	def contact_removed_callback( cls, sender=None, group=None, contact=None, **kwargs ):
		"""
		Callback handler for when a contact is *removed* from a group. Will execute defined
		actions for this group.
		"""
		logger.debug( "contact %s removed from group %s" % ( contact.pk, group.pk ) )
		for a in cls.get_actions( group, on_event='contact_removed' ):
			a.dispatch( group=group, contact=contact )

	@classmethod
	def contact_updated_callback( cls, sender=None, instance=None, dirty_fields={}, **kwargs ):
		"""
		Callback handler for when a local field is *updated*. Will execute defined actions for
		all groups for this contact.
		"""
		logger.debug( "contact %s updated" % instance.pk )
		updates = {}
		if dirty_fields:
			for attr, val in dirty_fields.items():
				updates[attr] = ( val, getattr( instance, attr, None ) )

			for group in instance.groups.all():
				for a in cls.get_actions( group, on_event='contact_updated' ):
					a.dispatch( instance=instance, changes=updates )

# ====================================================================
# Import-related models
# ====================================================================

class DataImportError( Exception ):
	pass

ISO_EXPANSION = {
	'ES' : [u'espana',u'españa'],
	'IT' : [u'italia',],
	'GB' : [u'uk',u'england',u'great britan',],
	'US' : [u'united states'],
	'NL' : [u'netherlands',u'holland'],
	'MX' : [u'méxico'],
}
		
DUPLICATE_HANDLING = [
	('none','Import all - no duplicate detection'),
	('ignore','Import non-duplicates only'),
	('update','Update existing contact'),
	('update_groups','Update existing contact (contact groups only)'),
]

MULTIPLE_DUPLICATES = [
	('ignore','None'),
	('first','First'),
	('create_new','Create new'),				
]

class ImportTemplate( models.Model ):
	"""
	An import template defines how a CSV or Excel file should be
	imported into the contacts model. It supports mapping columns
	to contacts fields.
	
	It also supports mapping columns to country and groups models.
	
	Mapping to a country is done in a fuzzy way, to allow for different
	spellings of a country name.
	"""
	
	name = models.CharField( max_length=255, unique=True )
	duplicate_handling = models.CharField( max_length=20, choices=DUPLICATE_HANDLING, help_text='' )
	multiple_duplicates = models.CharField( max_length=20, choices=MULTIPLE_DUPLICATES, help_text='Method use to select a duplicate in case multiple possible duplicates are found.' )
	
	tag_import = models.BooleanField( default=True, help_text="Create a contact group for this import.")
	extra_groups = models.ManyToManyField( ContactGroup, blank=True )
	
	_selectors_cache = None
	_mapping_cache = None
	
	class Meta:
		ordering = ['name',]
	
	def __unicode__(self):
		return self.name
		
	def get_selectors(self):
		if self._selectors_cache is None:
			self._selectors_cache = [x for x in ImportSelector.objects.filter( template=self )]
		return self._selectors_cache
	
	def is_selected( self, data ):
		"""
		Determine if a data row should be imported or not.
		"""
		selectors = self.get_selectors()

		if not selectors:
			return True
		
		for s in selectors:
			if s.is_selected( data ):
				return True
		return False
	
	def get_mapping( self ):
		if self._mapping_cache is None:
			self._mapping_cache = [x for x in ImportMapping.objects.filter( template=self )]
		return self._mapping_cache

	
	def parse_row( self, incoming_data, as_list=False, flat=False ):
		"""
		Transform the incoming data according to 
		the defined data mapping.
		"""
		if self.is_selected( incoming_data ):
			outgoing_data = [] if as_list else {}
			for m in self.get_mapping():
				val = m.get_value( incoming_data )

				if as_list:
					outgoing_data.append( ", ".join(val) if isinstance( val,list ) and flat else val )
				else:
					field = str( m.get_field() )
					if field in outgoing_data:
						outgoing_data[field] += val
					else:
						outgoing_data[field] = val
			return outgoing_data
		return None
	
	def get_importer( self, filename ):
		"""
		"""
		from djangoplicity.contacts.importer import CSVImporter, ExcelImporter
		
		base, ext = os.path.splitext( filename )
		extmap = {
			'.xls' : ExcelImporter,
			'.csv' : CSVImporter,
		}

		try:
			importercls = extmap[ext.lower()]
		except KeyError:
			raise DataImportError("Unsupported file format '%s'." % ext)
		
		return importercls( filename=filename )
		
	def extract_data( self, filename ):
		"""
		Extract data from an import file. Supported formats
		are currently, CSV and Excel (.xls).
		"""
		importer = self.get_importer( filename )
		return ( self.parse_row( row ) for row in importer )
		
	
	def preview_data( self, filename ):
		"""
		Preview the data file according to the defined
		import template.
		"""
		data_table = []
		i = 1 # Excel start with header at row 1
		for row in self.get_importer( filename ):
			i += 1
			data = self.parse_row( row, as_list=True, flat=True )
			if data:
				data.insert( 0, i )
				data_table.append( data )
		return ( ["Row"] + self.get_mapping(), data_table )
		
	def import_data( self, filename ):
		"""
		Import the data file according to the defined
		import template.
		"""
		if self.tag_import:
			import_grp, created = ContactGroup.objects.get_or_create( name='Import %s at %s' % ( self.name, datetime.now().replace( microsecond=0 ) ) )
		else:
			import_grp = None
			
		extra_groups = list(self.extra_groups.all().values_list( 'name', flat=True ))

		i = 0
		for data in self.extract_data( filename ):
			if data:
				i += 1
				if 'groups' in data:
					data['groups'] += extra_groups
				else:
					data['groups'] = extra_groups
				
				# Add import group if needed
				if import_grp:
					data['groups'].append( import_grp.name )
			
				if self.duplicate_handling != 'none':
					#
					# Duplicate handling
					#
					existing_obj = None
					qs = Contact.find_objects( **data )
					if qs and len( qs ) >= 1:
						if self.multiple_duplicates == 'first':
							existing_obj = qs[0] # Select first duplicate
						elif self.multiple_duplicates == 'ignore':
							continue # Ignore row
						elif  self.multiple_duplicates == 'create_new':
							existing_obj = None # Create new object instead
					elif qs and len( qs ) == 1:
						existing_obj = qs[0]
						
					# Check if existing object was found
					if existing_obj:
						if self.duplicate_handling == 'ignore':
							continue
						elif self.duplicate_handling == 'update':
							existing_obj.update_object( **data )

						if 'groups' in data and data['groups']:
							grps = ContactGroup.objects.filter( name__in=data['groups'] )
							if grps:
								existing_obj.groups.add( *grps )
						continue
				obj = Contact.create_object( **data )
				logger.info("Creating contact %s" % obj.pk )



CONTACTS_FIELDS = [
	('city','City'),
	('groups','Contact groups'),
	('country','Country'),
	('department','Department'),
	('email','Email'),
	('first_name','First name'),
	('last_name','Last name'),
	('organisation','Organisation'),
	('phone','Phone'),
	('position','Position'),
	('social','Social'),
	('street_1','Street 1'),
	('street_2','Street 2'),
	('title','Title'),
	('website','Website'),
]

class ImportMapping( models.Model ):
	"""
	Defines a mapping from a column in an CSV or Excel file to a contact model field.
	"""
	template = models.ForeignKey( ImportTemplate )
	header = models.CharField( max_length=255 )
	field = models.SlugField( max_length=255, choices=CONTACTS_FIELDS )
	group_separator = models.CharField( max_length=20, default='', blank=True )
	
	_country_cache = None
	_groupmap_cache = None

	def get_field( self ):
		"""
		"""
		trail = self.field.split("__")
		return trail[0]
	
	def get_country_value( self, value ):
		"""
		"""
		from djangoplicity.contacts.deduplication import similar_text
		
		if ImportMapping._country_cache is None:
			ImportMapping._country_cache = { 'iso' : {}, 'name' : {} }
			for c in Country.objects.all():
				ImportMapping._country_cache['iso'][c.iso_code.lower()] = c.iso_code
				ImportMapping._country_cache['name'][c.name.lower()] = c.iso_code
		
		value = value.lower().strip()
		if len(value) == 2 and value in ImportMapping._country_cache['iso']: 
			return ImportMapping._country_cache['iso']['value'].upper()
		elif value in ImportMapping._country_cache['name']:
			return ImportMapping._country_cache['name'][value].upper()
		else:
			for k,v in ImportMapping._country_cache['name'].items():
				if similar_text( k, value ):
					logger.info( "similar %s = %s" % (k,value) )
					return v.upper()

			for iso,exps in ISO_EXPANSION.items():
				for e in exps:
					if similar_text( unicode(value), e ):
						return iso.upper()
			return None
	
	def get_groups_value( self, value ):
		"""
		"""
		if self.field == 'groups' and self.group_separator:
			values = [x.strip() for x in value.split( self.group_separator )]
		else:
			values = [value.strip()]
		
		# Cache the mapping from values to contact groups so future queries are fast. 	
		if self._groupmap_cache is None:
			self._groupmap_cache = dict( ImportGroupMapping.objects.filter( mapping=self ).values_list( 'value', 'group__name' ) )
				
		return filter( lambda x: x, map( lambda x: self._groupmap_cache.get(x,None), values ) )
		
	def get_value( self, data ):
		"""
		Get the value for the model field. For most fields, this is just
		the direct value, however for groups and country there are special
		processing going on. 
		"""
		try:
			val = data[self.header]
			if self.field:
				trail = self.field.split("__")
				if trail[0] == 'groups':
					return self.get_groups_value( val )
				if trail[0] == 'country':
					return self.get_country_value( val )
			return val
		except KeyError:
			return None
	
	
class ImportSelector( models.Model ):
	"""
	Defines a selector for an import template. This allows
	the template to only import certain rows (e.g. if a specific
	column contains an x in a cell it will be imported).
	"""
	template = models.ForeignKey( ImportTemplate )
	header = models.CharField( max_length=255 )
	value = models.CharField( max_length=255 )
	case_sensitive = models.BooleanField( default=False )
	
	def get_value( self, data ):
		try:
			return data[self.header]
		except KeyError:
			return None
	
	def is_selected( self, data ):
		val = self.get_value( data )
		if val:
			val = unicode( val ).strip() if self.case_sensitive else unicode( val ).strip().lower()
		return val == self.value
	

class ImportGroupMapping( models.Model ):
	""" 
	Defines a mapping for values to a group
	"""
	mapping = models.ForeignKey( ImportMapping, limit_choices_to={ 'field' : 'groups' } )
	value = models.CharField( max_length=255 )
	group = models.ForeignKey( ContactGroup )
	

upload_dir = os.path.join( settings.TMP_DIR, 'contacts_import' )
upload_fs = FileSystemStorage( location=upload_dir, base_url=None )

def handle_uploaded_file( instance, filename ):
	"""
	"""
	base, ext = os.path.splitext( filename )
	
	import uuid
	name = "%s%s%s" % ( "%s_" % instance.template.name if instance.template else '', str( uuid.uuid1() ), ext.lower() )
	
	return name
	
class Import( models.Model ):
	template = models.ForeignKey( ImportTemplate )
	data_file = models.FileField( upload_to=handle_uploaded_file, storage=upload_fs )
	imported = models.BooleanField( default=False )
	created = models.DateTimeField( auto_now_add=True )
	last_modified = models.DateTimeField( auto_now=True )
	
	def preview_data( self ):
		"""
		"""
		return self.template.preview_data( self.data_file.path )
	
	def import_data( self ):
		"""
		"""
		if not self.imported:
			self.template.import_data( self.data_file.path )
			self.imported = True
			return True
		return False
	
	@classmethod
	def pre_delete_callback( cls, sender, instance=None, **kwargs ):
		"""
		"""
		try:
			instance.data_file.delete()
		except Exception:
			pass	

pre_delete.connect( Import.pre_delete_callback, sender=Import )

# Connect signals to clear the action cache
post_delete.connect( ContactGroupAction.clear_cache, sender=ContactGroupAction )
post_save.connect( ContactGroupAction.clear_cache, sender=ContactGroupAction )
post_delete.connect( ContactGroupAction.clear_cache, sender=Action )
post_save.connect( ContactGroupAction.clear_cache, sender=Action )
post_delete.connect( ContactGroupAction.clear_cache, sender=ContactGroup )
post_save.connect( ContactGroupAction.clear_cache, sender=ContactGroup )

# Connect signals needed to send out contac_added/contact_removed signals.
m2m_changed.connect( Contact.m2m_changed_callback, sender=Contact.groups.through )
pre_delete.connect( Contact.pre_delete_callback, sender=Contact )
pre_save.connect( Contact.pre_save_callback, sender=Contact )
post_save.connect( Contact.post_save_callback, sender=Contact )

# Connect signals to propagate Contact.group_order values 
pre_delete.connect( ContactGroup.pre_delete_callback, sender=ContactGroup )
post_delete.connect( ContactGroup.post_delete_callback, sender=ContactGroup )
pre_save.connect( ContactGroup.pre_save_callback, sender=ContactGroup )
post_save.connect( ContactGroup.post_save_callback, sender=ContactGroup )

# Connect signals handling the execution of actions
contact_added.connect( ContactGroupAction.contact_added_callback, sender=Contact )
contact_removed.connect( ContactGroupAction.contact_removed_callback, sender=Contact )
contact_updated.connect( ContactGroupAction.contact_updated_callback, sender=Contact )
