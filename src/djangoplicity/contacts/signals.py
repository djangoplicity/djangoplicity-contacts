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

"""
Django has a strange behavior for m2m_changed signal, so it is not easy to
get to know when a contact was added or removed to a group. These two signals should
alleviate that problem.

Django problem
==============
Using pure python everything works nicely::
	
	c= Contact.objects.get( ... )
	c.groups.add( .. )
	c.groups.remove( .. )

You will receive the m2m_changed signal 4 times with the actions:
  * pre_add
  * post_add
  * pre_remove
  * post_remove
   
However, if you now go to the admin and add/change a contact, then you would expect to get
the same m2m_changed signals. But in fact you get m2m_changed signals like this:
  
  * pre_clear
  * post_clear
  * pre_add
  * post_add

Django first delete all relations, and add the new ones. Hence, it's hard to know which
ones are actually removed. I guess they save one SQL query doing it this way. 
"""

from django.dispatch import Signal

contact_added = Signal( providing_args=[ "group", "contact", ] )
contact_removed = Signal( providing_args=[ "group", "contact", ] )
contact_updated = Signal(providing_args=[ "instance", "dirty_fields" ]) # Some field changed value