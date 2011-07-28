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
Module for generating labels in PDF documents. Relying on trml2pdf to generate the
PDFs. Works together with the ``Label`` class to define different labels.


Uses base templates to define a specific types of label paper with a standard
layout of each label. The layout of each label can be overwritten. The standard
labels assumes you are passing ``Contact`` models

Usage::
	>>> from djangoplicity.contacts.labels import LabelRender
	>>> from djangoplicity.contacts.models import Contact
	>>> queryset = Contacts.objects.all()[:100]
	>>> l = LabelRender( 'a4-l7165' )
	
	# Write a PDF file
	>>> l.render_file( queryset, 'somefilename.pdf', outputdir='/path/to/somewhere/', extra_context={ 'title' : 'Some Title', 'author' : 'Some Author' } )
	
	# Get a HTTP response with PDF file instead
	>>> l.render_http_response( queryset, 'somefilename.pdf', extra_context={ 'title' : 'Some Title', 'author' : 'Some Author' } )
	
	# Override default template layout and repeat each label 4 times.
	>>> style = '{% include "contacts/labels/cool_label_style.rml" %}'
	>>> template = '{% include "contacts/labels/cool_label.rml" %}'
	>>> l = LabelRender( 'a4-l7165', label_template=template, style=style, repeat=4 )
	
	# in the label template you have access to the variable ``obj`` which contains the
	# current object instance for the label you are rendering:
	>>> template = '...{{obj.email}}...'
	
	
When override templates, instead of including a template in a file, you can also just
directly define the django template in a string. This is used by the ``Label`` model to
define custom labels. 
"""

from django.template import loader, Context, Template
from django.utils.encoding import smart_str
from django.http import HttpResponse
import math
import os

try:
	import trml2pdf
except ImportError:
	trml2pdf = None
	
LABEL_PAPER = {
	'a4-l7163' : { 
		'title' : 'A4 (L7163 - 99.1x38.1)', 
		'labels_no' : 14,
		'template' : "contacts/labels/a4-l7163.rml", 
		'label_template' : 'contacts/labels/standard_label_small.rml',
		'label_template_style' : 'contacts/labels/standard_label_small_style.rml',
	},
	'a4-l7165' : { 
		'title' : 'A4 (L7165 - 99.1x67.7)', 
		'labels_no' : 8,
		'template' : "contacts/labels/a4-l7165.rml", 
		'label_template' : 'contacts/labels/standard_label.rml',
		'label_template_style' : 'contacts/labels/standard_label_style.rml',
	},
}
"""
Variable defines all possible paper types. For each paper type following properties 
are defined:
    * ``labels_no``: Number of labels per page
    * ``template``: The RML template for the paper type
    * ``label_template``: The default RML template file for layout of one label (the 
        template file is included once for each label in template)
    * ``label_template_style``:  The default extra RML stylesheet which may be needed
        by label_template
"""

LABEL_PAPER_CHOICES = tuple( [( k, v['title'] ) for k, v in LABEL_PAPER.items()] )
""" Label paper choices for use as choices in a django field. """


class LabelRender( object ):
	"""
	Class that renders labels from a queryset.
	"""
	
	def __init__( self, paper, label_template=None, style=None, repeat=1 ):
		"""
		Initialise template render.
		
		    * ``paper``: a  key in LAPER_PAPER (required)
		    * ``label_template``: string with a django template to use instead of the default label template (optional)
		    * ``style``: string with a django template to use instead of the default label template style (optional)
		    * ``repeat``: the number of times to repeat each object in the query set.   
		"""
		# Ensure trml2pdf is installed
		if trml2pdf is None:
			raise Exception( "Cannot generate PDF - trml2pdf is not installed." )
		
		# Check paper type
		if paper not in LABEL_PAPER:
			raise Exception( "Label paper %s is not defined." )

		# The render works by generating a template which looks like this: 
		# {% extends "contacts/labels/<papertype>.rml" %}
		# {% block label_style %}<label_template_style>{% endblock %}
		# {% block label0 %}<label_template>{% endblock %}
		# {% block label1 %}<label_template>{% endblock %}
		# ...
		# {% block label<label_no-1> %}<label_template>{% endblock %}
		# 
		# Hence, the <papertype>.rml template must naturally define these blocks:
		# 1 block for the label_style
		# X blocks for the individual labels on a page.
		self.label_paper = LABEL_PAPER[paper]
		self.document_template = """{%% extends "%s" %%}""" % self.label_paper['template']
		
		if style:
			self.document_template += u"""{%% block label_style %%}%s{%% endblock %%}""" % style
		if label_template:
			for i in range( self.label_paper['labels_no'] ):
				self.document_template += u"""{%% block label%s %%}%s{%% endblock %%}""" % ( i, label_template )
		
		self.document_template = Template( self.document_template )
		self.repeat = repeat if int(repeat) > 0 else 1
		
		
	def render( self, queryset, filename, extra_context={} ):
		"""
		Render PDF. 
		
		It is possible to simply extra context variables to the 
		templates via extra_context. However, the following keys
		are reserved:
		
			* filename
			* label_template
			* label_template_style
			* objects
			
		For instance most templates support these extra variables:
	
			* title
			* label_template
		"""
		# Repeat objects in queryset if needed.
		if self.repeat > 1:
			new_queryset = []
			for obj in queryset:
				new_queryset += [obj] * self.repeat
			queryset = new_queryset
		
		# Split queryset into lists of pages
		list_count = int( math.ceil( float( len( queryset ) ) / self.label_paper['labels_no'] ) )
		
		page_objects = []
		for i in range( list_count ):
			page_objects.append( queryset[i * self.label_paper['labels_no']:( i + 1 ) * self.label_paper['labels_no']] )
		
		if len( page_objects[-1] ) != self.label_paper['labels_no']:
			page_objects[-1] = page_objects[-1] + [None] * ( self.label_paper['labels_no'] - len( page_objects[-1] ) )
		
		# Generate context
		extra_context.update( {
			'filename' : filename,
			'label_template' : self.label_paper['label_template'],
			'label_template_style' : self.label_paper['label_template_style'],
			'objects' : page_objects,
		} )
		
		# Generate RML template
		rmldoc = self.document_template.render( Context( extra_context ) )

		# Generate PDF
		return trml2pdf.parseString( smart_str( rmldoc ) )
	
		
	def render_http_response( self, queryset, filename, response=None, extra_context={} ):
		"""
		Write rendered PDF to a HttpResponse object.
		"""
		if response is None:
			response = HttpResponse( mimetype='application/pdf' )
		response['Content-Disposition'] = 'attachment; filename=%s' % filename
		response.write( self.render( queryset, filename, extra_context=extra_context ) )
		return response
	
	def render_file( self, queryset, filename, outputdir=None, extra_context={} ):
		"""
		Write rendered PDF to a file in a output directory.
		"""
		if outputdir is None:
			outputdir = os.getcwd()
		
		if not os.path.exists( outputdir ):
			raise Exception( "Output directory does not exists" )
		
		fullpath = os.path.join( outputdir, filename )
		
		f = open( fullpath, 'w' )
		f.write( self.render( queryset, filename, extra_context=extra_context ) )
		f.close()
		
		return fullpath
