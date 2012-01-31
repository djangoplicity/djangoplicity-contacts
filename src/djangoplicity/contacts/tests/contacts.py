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
from djangoplicity.contacts.models import Field, Country, ContactGroup, Contact
from djangoplicity.contacts.tests.testdata import ContactSetupMixin

class ContactUpdateTestCase( ContactSetupMixin, TestCase ):
	"""
	Test case for updating of contacts 
	"""
	
	def test_simple_all( self ):
		""" 
		Test update of all simple properties
		"""
		c1 = Contact.objects.get( id=1 )
		c4_data = self.create_contact( 4 ) # Id also set in data, but should not get updated

		# Run update
		c1.update_object( **c4_data )
		
		# Check updated attributes
		for k,v in c4_data.items():
			if k == 'id':
				self.assertEqual( getattr( c1, k ), c1.id )				
			else:
				self.assertEqual( getattr( c1, k ), v )
		
		# Make sure we can save the changes as well
		c1.save() 
	
	def test_simple_few( self ):
		"""
		Test update of simple properties
		"""
		c2 = Contact.objects.get( id=2 )
		data = { 'website' : 'newwensite', 'email' : 'new@email' }
		c2.update_object( **data )
		
		for k, v in self.create_contact( 2 ).items():
			if k in data:
				self.assertEqual( getattr( c2, k ), data[k] ) # Update
			else:
				self.assertEqual( getattr( c2, k ), v ) # No update

		# Make sure we can save the changes as well				
		c2.save()
		
	def test_extra_fields( self ):
		"""
		Test update of extra fields
		"""
		field_slug = self.fields[0].slug
		c1 = Contact.objects.get( id=1 )
		data = { 'website' : 'newwensite', field_slug : 'new_extra_field' }
		c1.update_object( **data )
		
		self.assertEqual( c1.website, data['website'] )
		self.assertEqual( c1.get_extra_field( field_slug ), data[field_slug] )
		
	def test_country( self ):
		"""
		Test update of country
		"""
		# Set by name
		c1 = Contact.objects.get( id=1 )
		country = self.countrys[1]
		data = { 'country' : country.name }
		c1.update_object( **data )
		self.assertEqual( c1.country.pk, country.pk )
		c1.save()
		
		# Set by iso code
		country = self.countrys[0]
		data = { 'country' : country.iso_code }
		c1.update_object( **data )
		c1.save()
		c1 = Contact.objects.get( id=1 )
		self.assertEqual( c1.country.pk, country.pk )
	
	def test_city( self ):
		"""
		Test update using city, zip, state with/without country 
		"""
		# Without country
		#
		c2 = Contact.objects.get( id=2 )
		c3 = Contact.objects.get( id=3 ) 
		self.assertEqual( c2.country.zip_after_city, False )
		self.assertEqual( c3.country.zip_after_city, True )
		
		data = { 'city' : 'city', 'zip' : 'zip', 'state' : 'state', 'first_name' : 'first_name' }
		c2.update_object( **data )
		c3.update_object( **data )
		
		self.assertEqual( c2.city, "zip  city  state" )
		self.assertEqual( c3.city, "city  state  zip" )
		self.assertEqual( c2.first_name, "first_name" )
		self.assertEqual( c3.first_name, "first_name" )
		
		data = { 'city' : 'city', 'postal_code' : 'postal_code', 'state' : 'state',  }
		c2.update_object( **data )
		c3.update_object( **data )
		
		self.assertEqual( c2.city, "postal_code  city  state" )
		self.assertEqual( c3.city, "city  state  postal_code" )
		
		# With country
		data = { 'city' : 'city', 'zip' : 'zip', 'state' : 'state', 'country' : 'US' }
		c2.update_object( **data )
		self.assertEqual( c2.city, "city  state  zip" )
		
		data = { 'city' : 'city', 'zip' : 'zip', 'state' : 'state', 'country' : 'DK' }
		c2.update_object( **data )
		self.assertEqual( c2.city, "zip  city  state" )
				
				
		
class ContactCreateTestCase( ContactSetupMixin, TestCase ):
	def test_create( self ):
		extras = { 'country' : 'DK', 'skype' : 'c5.skype', 'groups' : ['G1', 'G5'] }
		data = self.create_contact( 5, extra=extras )
		c5 = Contact.create_object( **data )
		
		self.assertEqual( c5.pk, 4 ) # Id should not be taken into account
		
		for k,v in data.items():
			if k not in extras and k != 'id':
				self.assertEqual( getattr( c5, k ), v )
				
		self.assertEqual( c5.country.iso_code, 'DK' )
		self.assertEqual( c5.get_extra_field( 'skype' ), 'c5.skype' )
		self.assertEqual( [x.name for x in c5.groups.all().order_by( 'name' )], extras['groups'] )
			
