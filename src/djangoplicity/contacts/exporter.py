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

import xlwt
import datetime
import decimal

class Exporter( object ):
	"""
	Abstract base class for all exporters
	"""
	def __init__( self, header=[] ):
		self._wrote_header = False
		self._header_mapping = {}
		self._header = []
		i = 0

		for h, func in header:
			self._header.append( h )
			self._header_mapping[h] = {'func': func, 'idx' : i}
			i += 1

	def _prepare_row( self, data ):
		row = []
		for h in self._header:
			func = self._header_mapping[h]['func']
			try:
				val = data[h]
				if func:
					val = func( val )
			except KeyError:
				val = None
			row.append( val )
		return row
	
	def writeheader( self, **kwargs ):
		if not self._wrote_header:
			self._wrote_header = True
			self.writerow( self._header, **kwargs )

	def writedata( self, data, **kwargs ):
		row = self._prepare_row( data )
		self.writerow( row, **kwargs )

	def writerow( self, row, **kwargs ):
		raise NotImplementedError

	def writerows( self, rows, **kwargs ):
		for r in rows:
			self.writerow( r )


class ExcelExporter( Exporter ):
	"""
	Excel exporter
	
	Example:: 
		exporter = ExcelExporter( filename_or_stream='/path/to/excelfile.xls', header=[ ('id',None), ('email', None) ] )
		for obj in queryset:
			exporter.writedata( { 'id' : obj.id, 'email' : obj.email } )
		exporter.save()
	"""
	mimetype = "application/vnd.ms-excel"
	
	styles = {
		'datetime' : xlwt.easyxf( num_format_str="YYYY/MM/DD hh:mm:ss" ),
		'date' : xlwt.easyxf( num_format_str="YYYY/MM/DD" ),
		'time' : xlwt.easyxf( num_format_str="hh:mm:ss" ),
	}
	
	def __init__( self, filename_or_stream=None, title="Contacts", header=[], flush_rows=500 ):
		super( ExcelExporter, self ).__init__( header=header )
		self._out = filename_or_stream
		self._wb = xlwt.Workbook()
		self._ws = self._wb.add_sheet( title )
		self._row = 0
		self._flush_rows = flush_rows
		self.writeheader()

	def save( self, filename_or_stream=None ):
		self._wb.save( filename_or_stream if filename_or_stream else self._out )
		
	def writeheader( self, **kwargs ):
		defaults = { 'style' : xlwt.easyxf( 'font: bold on, colour white; pattern: pattern solid, fore-colour black' ) }
		defaults.update( kwargs )
		super( ExcelExporter, self ).writeheader( **defaults )

	def _prepare_value( self, value ):
		if (isinstance( value, basestring ) or 
			isinstance( value, int ) or
			isinstance( value, float ) or
			isinstance( value, long ) or
			isinstance( value, decimal.Decimal ) or
			isinstance( value, bool ) or
			isinstance( value, decimal.Decimal ) or
			value is None):
			return [value]
		elif isinstance( value, datetime.datetime ):
			return [value,self.styles['datetime']]
		elif isinstance( value, datetime.date ):
			return [value,self.styles['date']]
		elif isinstance( value, datetime.time ):
			return [value,self.styles['time']]
		else:
			return [unicode( value )]
		
	def _prepare_values( self, values ):
		return map( lambda x: self._prepare_value( x ), values )

	def writerow( self, row, style=None, **kwargs ):
		i = 0
		for cval in row:
			if style is not None:
				self._ws.write( self._row, i, self._prepare_value(cval)[0], style )
			else:
				self._ws.write( self._row, i, *self._prepare_value(cval) )
			i += 1
		# Writing large amount of data requires the sheet to be flushed from time to time 
		# otherwise a "ValueError: More than 4094 XFs (styles)" error is thrown.
		# Once the rows are flushed, they can no longer be edited. 
		if self._flush_rows > 0 and self._row % self._flush_rows == 0:
			self._ws.flush_row_data() 
		self._row += 1