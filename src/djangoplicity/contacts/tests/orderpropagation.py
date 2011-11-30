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

from django.test import TestCase
from djangoplicity.contacts.models import Contact, ContactGroup

class OrderPropagationTestCase( TestCase ):
	"""
	Testing that the ContactGroup.order is propagated 
	correctly to Contact.group_order.
	"""

	def _clean( self ):
		"""
		Setup contacts and groups
		"""
		ContactGroup.objects.all().delete()
		Contact.objects.all().delete()
		Contact.groups.through.objects.all().delete()

		self.c1 = Contact()
		self.c2 = Contact()
		self.contacts = [self.c1, self.c2]

		self.g1 = ContactGroup( name='g1', order=1 )
		self.g2 = ContactGroup( name='g2', order=2 )
		self.g3 = ContactGroup( name='g3', order=3 )
		self.groups = [self.g1, self.g2, self.g3]

		for x in self.contacts + self.groups:
			x.save()

	def _check( self, contact, expected ):
		"""
		Check value of Contact.group_order
		"""
		self.assertEqual( Contact.objects.get( pk=contact.pk ).group_order, expected )

	def test_add_group( self ):
		"""
		Adding groups to a contact and propagating the ContactGroup.order value
		"""
		self._clean()

		# Initial condition
		self._check( self.c1, None )

		# New order value
		self.c1.groups.add( self.g2 )
		self._check( self.c1, self.g2.order )

		# Lower order value
		self.c1.groups.add( self.g1 )
		self._check( self.c1, self.g1.order )

		# Higher order value
		self.c1.groups.add( self.g3 )
		self._check( self.c1, self.g1.order )

	def test_remove_group( self ):
		"""
		Removing groups from a contact and propagating the ContactGroup.order value
		"""
		self._clean()

		# Remove group with higher value - group_order value does *not* change
		self.c1.groups.add( self.g1 )
		self.c1.groups.add( self.g2 )
		self._check( self.c1, self.g1.order )

		self.c1.groups.remove( self.g2 )
		self._check( self.c1, self.g1.order )

		# Remove group with lower value - group_order value *does* change
		self.c2.groups.add( self.g1 )
		self.c2.groups.add( self.g2 )
		self._check( self.c2, self.g1.order )

		self.c2.groups.remove( self.g1 )
		self._check( self.c2, self.g2.order )
		
	def test_clear_groups( self ):
		"""
		Removing groups from a contact and propagating the ContactGroup.order value
		"""
		self._clean()

		# Remove group with higher value - group_order value does *not* change
		self.c1.groups.add( self.g1 )
		self.c1.groups.add( self.g2 )
		self._check( self.c1, self.g1.order )

		self.c1.groups.clear()
		self._check( self.c1, None )
		

	def test_change_group( self ):
		"""
		Changing the order value
		"""
		self._clean()
		
		self.c1.groups.add( self.g1 )
		self.c1.groups.add( self.g2 )
		self.c2.groups.add( self.g2 )
		self.c2.groups.add( self.g3 )
		self._check( self.c1, self.g1.order )
		self._check( self.c2, self.g2.order )
		
		# No propagation
		self.g1.name = 'TEST'
		self.g1.save()
		self._check( self.c1, self.g1.order )
		self._check( self.c2, self.g2.order )
		
		# Change to a lower value - group_order value updated to new value
		self.g1.order = 0
		self.g1.save()
		
		self._check( self.c1, self.g1.order )
		self._check( self.c2, self.g2.order )
		
		print "g1 0 -> 1"
		self.g1.order = 1
		self.g1.save()
		
		print self.c1.groups.all().values_list('order')
		
		self._check( self.c1, self.g1.order )
		self._check( self.c2, self.g2.order )
		
		# Change to a higher value - group_order value is updated to a another groups value
		self.g1.order = 4
		self.g1.save()
		
		self._check( self.c1, self.g2.order )
		self._check( self.c2, self.g2.order )
		
		# Change to a higher value - no changes
		self.g1.order = 5
		self.g1.save()
		
		self._check( self.c1, self.g2.order )
		self._check( self.c2, self.g2.order )
		
		# Change multiple
		self.g2.order = 1
		self.g2.save()
		
		self._check( self.c1, self.g2.order )
		self._check( self.c2, self.g2.order )
		
		self.g1.order = 0
		self.g1.save()
		
		self._check( self.c1, self.g1.order )
		self._check( self.c2, self.g2.order )


	def test_delete_group( self ):
		"""
		Deleting a group
		"""
		self._clean()
		
		self.c1.groups.add( self.g1 )
		self.c1.groups.add( self.g2 )
		self.c2.groups.add( self.g2 )
		self.c2.groups.add( self.g3 )
		self._check( self.c1, self.g1.order )
		self._check( self.c2, self.g2.order )

		self.g1.delete()
		
		self._check( self.c1, self.g2.order )
		self._check( self.c2, self.g2.order )
		
		self.g3.delete()
		
		self._check( self.c1, self.g2.order )
		self._check( self.c2, self.g2.order )
		
		self.g2.delete()
		
		self._check( self.c1, None )
		self._check( self.c2, None )
		