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

import os

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
	
	def __unicode__(self):
		return self.name
	
	class Meta:
		ordering = ['name']

class GroupCategory( models.Model ):
	"""
	Groupings of groups.
	"""
	name = models.CharField( max_length=255, blank=True )
	
	def __unicode__(self):
		return self.name
	
	class Meta:
		verbose_name_plural = 'group categories'
		ordering = ('name',)


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

class Country( models.Model ):
	"""
	Country model for storing country names.
	"""
	name = models.CharField( max_length=40, db_index=True )
	iso_code = models.CharField( _( 'ISO code' ), max_length=5, blank=True )
	dialing_code = models.CharField( max_length=10, blank=True )
	zip_after_city = models.BooleanField( default=False )
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

	def save(self, *args, **kwargs ):
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
	
	def __unicode__(self):
		return self.name
		#return "%s: %s" % (self.category, self.name) if self.category else self.name
	
	class Meta:
		ordering = ( 'name', )


class Contact( models.Model ):
	"""
	Contacts model
	"""
	first_name = models.CharField( max_length=255, blank=True )
	last_name = models.CharField( max_length=255, blank=True )
	title = models.CharField( max_length=50, blank=True )
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
		data['name'] = ("%s %s %s" % ( self.title, self.first_name, self.last_name )).strip()
		data['address_lines'] = [x.strip() for x in self.organisation, self.department, self.street_1, self.street_2]
		data['city'] = self.city.strip()
		data['email'] = self.email.strip()
		data['country'] = self.country.iso_code.upper() if self.country else ''
		data['contact_object'] = self
		return data
	
	def __unicode__( self ):
		if self.first_name or self.last_name:
			return ("%s %s %s" % ( self.title, self.first_name, self.last_name )).strip()
		elif self.organisation:
			return self.organisation
		elif self.department:
			return self.department
		else:
			return self.pk

	class Meta:
		ordering = ['last_name']
		

class ContactField( models.Model ):
	"""
	Stores a field value for a given contact.
	"""
	field = models.ForeignKey( Field )
	contact = models.ForeignKey( Contact )
	value = models.CharField( max_length=255, blank=True )
	
	def __unicode__( self ):
		return "%s: %s" % ( self.field.name, self.value )
	
	def clean(self):
		if not self.field.blank and self.value == '':
			raise ValidationError( "Field %s does not allow blank values" % self.field )
	
	class Meta:
		unique_together = ( 'field', 'contact' )