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

LABEL_PAPER_CHOICES = tuple( [( k, v['title'] ) for k, v in LABEL_PAPER.items()] )


class LabelRender( object ):
	"""
	Class that renders labels from a queryset
	"""
	
	def __init__( self, paper, label_template=None, style=None, repeat=1 ):
		if trml2pdf is None:
			raise Exception( "Cannot generate PDF - trml2pdf is not installed." )
		
		if paper not in LABEL_PAPER:
			raise Exception( "Label paper %s is not defined." )

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
