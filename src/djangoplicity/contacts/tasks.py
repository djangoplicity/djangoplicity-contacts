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

from celery.schedules import crontab
from celery.task import PeriodicTask
from datetime import timedelta
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from djangoplicity.actions.plugins import ActionPlugin

class PeriodicAction( PeriodicTask ):
	"""
	Dispatch periodic actions for groups.
	"""
	abstract = True
	on_event_name = None

	def run( self ):
		"""
		"""
		logger = self.get_logger()

		from djangoplicity.contacts.models import ContactGroupAction, ContactGroup

		if self.on_event_name is None:
			raise ImproperlyConfigured( "on_event_name must be specified on class %s" % self.__class__.name )

		logger.info( "Dispatching periodic actions with event %s" % self.on_event_name )

		actions_by_group = ContactGroupAction.get_actions_for_event( self.on_event_name )
		group_pks = [int( x ) for x in actions_by_group.keys()]

		if group_pks:
			for group in ContactGroup.objects.filter( pk__in=group_pks ):
				for a in actions_by_group[str( group.pk )]:
					a.dispatch( group=group )


class Every5minAction( PeriodicAction ):
	run_every = timedelta( minutes=5 )
	on_event_name = 'periodic_5min'

class Every30minAction( PeriodicAction ):
	run_every = timedelta( minutes=30 )
	on_event_name = 'periodic_30min'

class EveryHourAction( PeriodicAction ):
	run_every = timedelta( hours=1 )
	on_event_name = 'periodic_1hr'

class Every6HourAction( PeriodicAction ):
	run_every = timedelta( hours=6 )
	on_event_name = 'periodic_6hr'

class EveryDayAction( PeriodicAction ):
	run_every = timedelta( hours=24 )
	on_event_name = 'periodic_1day'

#
# Contact actions
#	
class ContactAction( ActionPlugin ):
	"""
	An action plugin is a configurable celery task,
	that can be dynamically connected to events in the system.
	"""
	abstract = True

	def _get_group( self, group_name ):
		"""
		Get a group by its name
		"""
		from djangoplicity.contacts.models import ContactGroup
		return ContactGroup.objects.get( name=group_name )

	def _get_object( self, model_identifier, pk ):
		"""
		Helper method to get the object by model_identifier and primiary key ( e.g "contacts.contact" and 2579 )
		"""
		Model = models.get_model( *model_identifier.split( "." ) )
		return Model.objects.get( pk=pk )


class UpdateContactAction( ContactAction ):
	action_name = 'Contact update'
	action_parameters = [
		#( 'group', 'Name of group to assign to/remove from contact.', 'str' ),
	]
	
	@classmethod
	def get_arguments( cls, conf, *args, **kwargs ):
		"""
		"""
		from djangoplicity.contacts.models import Contact

		try:
			model_identifier = kwargs['model_identifier']
			pk = kwargs['pk']
		except KeyError:
			model_identifier = None
			pk = None
					
		defaults = { 'model_identifier' : model_identifier, 'pk' : pk }
	
		for k, v in kwargs.items():
			if k in Contact.ALLOWED_FIELDS:
				defaults[k] = v

		return ( [], defaults )

	def run( self, conf, model_identifier=None, pk=None, **kwargs ):
		"""
		Update contact based on new field values in kwargs.
		"""
		from djangoplicity.contacts.models import Contact

		
		if model_identifier == 'contacts.contact' and pk:
			contact = self._get_object( model_identifier, pk )
			
			defaults = {}
			for k, v in kwargs.items():
				if k in Contact.ALLOWED_FIELDS:
					defaults[k] = v
			
			if contact.update( **defaults ):
				contact.save()
				self.get_logger().info( "Contact %s was updated." % ( contact.pk ) )
			else:
				self.get_logger().info( "Contact %s was not updated." % ( contact.pk ) )


class UnsetContactGroupAction( ContactAction ):
	action_name = 'Contacts remove group'
	action_parameters = [
		( 'group', 'Name of group to assign to/remove from contact.', 'str' ),
	]
	
	@classmethod
	def get_arguments( cls, conf, *args, **kwargs ):
		"""
		"""
		try:
			model_identifier = kwargs['model_identifier']
			pk = kwargs['pk']
		except KeyError:
			model_identifier = None
			pk = None

		return ( [], { 'model_identifier' : model_identifier, 'pk' : pk } )

	def run( self, conf, model_identifier=None, pk=None ):
		"""
		Remove from a group from a contact. 
		"""
		from djangoplicity.contacts.models import Contact

		if model_identifier == 'contacts.contact' and pk:
			contact = self._get_object( model_identifier, pk )
			group = self._get_group( conf['group'] )

			contact.groups.remove( group )
			self.get_logger().info( "Removed contact %s from group %s." % ( contact.pk, group.name ) )


class RemoveEmailAction( ContactAction ):
	action_name = 'Contacts clean email'
	action_parameters = [
		( 'clear', 'Clear the email field for all contacts with this email', 'bool' ),
		( 'append', 'If clear is False, append the text in this field to contacts with this email (unless the field is empty)', 'str' ),
	]

	@classmethod
	def get_arguments( cls, conf, *args, **kwargs ):
		"""
		"""
		try:
			email = kwargs['email']
		except KeyError:
			email = None

		return ( [], { 'email' : email } )

	def run( self, conf, email=None ):
		"""
		Remove from a group from a contact. 
		"""
		from djangoplicity.contacts.models import Contact

		if email:
			num = 0
			if conf['clear']:
				num = Contact.objects.filter( email__iexact=email ).update( email='' )
			elif conf['append']:
				num = Contact.objects.filter( email__iexact=email ).update( email=email.lower() + conf['append'] )

			if num > 0:
				self.get_logger().info( "Removed invalid email address %s from %s contact(s)." % ( email, num ) )


UnsetContactGroupAction.register()
RemoveEmailAction.register()
UpdateContactAction.register()