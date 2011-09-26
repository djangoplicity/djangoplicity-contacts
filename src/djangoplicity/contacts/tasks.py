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

from celery.task import PeriodicTask
from celery.schedules import crontab
from django.core.exceptions import ImproperlyConfigured
from datetime import timedelta

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


class Every1minAction( PeriodicAction ):
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