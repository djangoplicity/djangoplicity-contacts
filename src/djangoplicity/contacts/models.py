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


from django.db import models
from django.forms import ValidationError
from django.template import loader, Context, Template
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _
from djangoplicity.contacts.labels import LabelRender, LABEL_PAPER_CHOICES
from djangoplicity.contacts.signals import contact_added, contact_removed, contact_updated
from django.db.models.signals import m2m_changed, pre_delete, post_delete, post_save, pre_save
from django.core.cache import cache
from djangoplicity.actions.models import Action
from dirtyfields import DirtyFieldsMixin

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


class ContactGroup( models.Model ):
	"""
	Groups for contacts
	"""
	name = models.CharField( max_length=255, blank=True )
	category = models.ForeignKey( GroupCategory, blank=True, null=True )

	def __unicode__( self ):
		return self.name
		#return "%s: %s" % (self.category, self.name) if self.category else self.name

	class Meta:
		ordering = ( 'name', )

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
		old_groups = self.get_snapshot(action)
		# Signals only sent if snapshot was created with the same action
		if old_groups is not None:
			logger.debug( "dispatch_signals:%s" % action)
			new_groups = set(self.groups.all())
			# added groups
			for g in new_groups - old_groups:
				logger.debug( "send contact_added")
				contact_added.send( sender=self.__class__, group=g, contact=self )
				
			# removed groups
			for g in old_groups - new_groups:
				logger.debug( "send contact_removed")
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
		logger.debug( "m2m_changed:%s"  % action )
		if action in ['pre_clear', 'pre_remove', 'pre_add']:
			instance.create_snapshot(action[4:])
		elif action in ['post_clear', 'post_remove', 'post_add']:
			instance.dispatch_signals(action[5:])
		

	@classmethod
	def pre_delete_callback( cls, sender, instance=None, **kwargs ):
		"""
		Callback is used to send contact_removed, contact_added signals
		"""
		logger.debug( "pre_delete" )
		for g in instance.groups.all():
			contact_removed.send_robust( sender=cls, group=g, contact=instance )
	
	@classmethod		
	def pre_save_callback( cls, sender, instance=None, raw=False, **kwargs ):
		"""
		Callback for detecting changes to the model.
		"""
		logger.debug( "pre_save" )
		instance._dirty_fields = instance.get_dirty_fields()
			
	@classmethod		
	def post_save_callback( cls, sender, instance=None, raw=False, **kwargs ):
		"""
		Callback for detecting changes to the model.
		"""
		logger.debug( "post_save" )
		dirty_fields = instance._dirty_fields
		instance._dirty_fields = None
		if dirty_fields != {}:
			logger.debug( "send contact_updated")
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
		return "%s: %s" % ( self.field.name, self.value )

	def clean( self ):
		if not self.field.blank and self.value == '':
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
	def get_actions( cls, group, on_event=None ):
		"""
		Get all actions defined for a certain group.
		
		Caches result to prevent many queries to the database. Currently the entire
		table is cached, however in case of issues, this caching strategy can be improved.
		"""
		action_cache = cache.get( cls._key )

		# Prime cache if needed
		if action_cache is None:
			logger.debug( "generating action cache" )
			action_cache = {}
			for a in cls.objects.all().select_related( depth=1 ).order_by( 'group', 'on_event', 'action' ):
				g_pk = str( a.group.pk )				
				if g_pk not in action_cache:
					action_cache[ g_pk ] = {}
				if a.on_event not in action_cache[g_pk]:
					action_cache[ g_pk ][a.on_event] = []
				action_cache[ g_pk ][a.on_event].append( a.action )
			
			cache.set( cls._key, action_cache )
		
		# Find actions for this group 
		try:
			actions = action_cache[ str( group.pk ) ]
			return actions if on_event is None else actions[on_event]
		except KeyError:
			return []


	@classmethod
	def contact_added_callback( cls, sender=None, group=None, contact=None, **kwargs ):
		"""
		Callback handler for when a contact is *added* to a group. Will execute defined
		actions for this group.
		"""
		logger.debug( "contact %s added to group %s" % (contact.pk, group.pk) )
		for a in cls.get_actions( group, on_event='contact_added' ): 
			a.dispatch( group=group, contact=contact )

	@classmethod
	def contact_removed_callback( cls, sender=None, group=None, contact=None, **kwargs ):
		"""
		Callback handler for when a contact is *removed* to a group. Will execute defined
		actions for this group.
		"""
		logger.debug( "contact %s removed from group %s" % (contact.pk, group.pk) )
		for a in cls.get_actions( group, on_event='contact_removed' ):
			a.dispatch( group=group, contact=contact )
			
	@classmethod
	def contact_updated_callback( cls, sender=None, instance=None, dirty_fields={}, **kwargs ):
		"""
		Callback handler for when a local field is *updated*. Will execute defined actions for
		all groups for this contact.
		"""
		# TODO: figure out how to connect MailmanUpdate action with an email being updated.
		logger.debug( "contact %s updated"  % instance.pk )
		updates = {}
		if dirty_fields:
			for attr, val in dirty_fields.items():
				updates['from_%s' % attr] = val
				updates['to_%s' % attr] = getattr( instance, attr, None )
		
			for group in instance.groups.all(): 
				for a in cls.get_actions( group, on_event='contact_updated' ):
					a.dispatch( instance=instance, **updates )


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

# Connect signals handling the execution of actions
contact_added.connect( ContactGroupAction.contact_added_callback, sender=Contact )
contact_removed.connect( ContactGroupAction.contact_removed_callback, sender=Contact )
contact_updated.connect( ContactGroupAction.contact_updated_callback, sender=Contact )

