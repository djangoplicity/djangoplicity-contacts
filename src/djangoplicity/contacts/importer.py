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
Helper classes for iterating over data in tabular data located in CSV/Excel files.

An important restriction for all tabular data files are that they must have
  * a header row and,
  * unique column names.


Usage example::

	# First construct an importer.
	>>> importer = CSVImporter( filename='/path/to/csvfile.csv' )
	>>> importer = ExcelImporter( filename='/path/to/excelfile.xls', sheet=1 )

	# Iterate over rows in tabular data
	>>> for row in importer:
	...	 for c in importer.keys(): # Iterator over each column
	...		 print row[c]

	# Extract column and iterate over all values
	>>> column_values = importer['SomeColumnName']
	>>> for val in column_values:
	...	 print val

 	# Get number of rows in tabular data
 	>>> number_of_rows = len(importer)

 	# Check if column exists in importer
 	>>> test = 'SomeColumnName' in importer

 	# Get all column names in importer
 	>>> header = importer.keys()

 	# Get a list of all column values
 	>>> header = importer.values()

 	#
 	>>> for column,values in importer.items()
 	...	 print column
 	...	 for v in values:
 	...		 print v

"""

import codecs
import csv
import xlrd


# ============
# Base classes
# ============
class Importer( object ):
	"""
	Abstract base class for all importers
	"""
	def __init__( self, *args, **kwargs ):
		self.cols = {}

	def __iter__( self ):
		return ImportIterator()

	def __len__( self ):
		return 0

	def __getitem__( self, value ):
		raise KeyError

	def __contains__( self, value ):
		"""
		Test if column name exists in excel file.
		"""
		return value in self.cols.keys()

	def keys( self ):
		"""
		Return all column names.
		"""
		return self.cols.keys()

	def items( self ):
		return [( c, self[c] ) for c in self.keys()]

	def values( self ):
		return [self[c] for c in self.keys()]


class ImportIterator( object ):
	"""
	Abstract base class for all import iterators.
	"""
	def __iter__( self ):
		return self

	def next( self ):
		raise StopIteration


# ==============
# Excel Importer
# ==============
class ExcelImporter( Importer ):
	"""
	Importer for Excel files.

	Defaults:
		sheet = 0
	"""
	def __init__( self, filename=None, sheet=0 ):
		"""
		Initialize importer by opening the Excel file and
		reading out a specific sheet.
		"""
		self.sheet = xlrd.open_workbook( filename ).sheet_by_index( sheet )

		i = 0
		self._header = []
		self.cols = {}
		for c in self.sheet.row_values( 0 ):
			if isinstance(c, basestring):
				c = c.strip()
			self.cols[c] = i
			self._header.append( ( c, None ) )
			i += 1

	def header( self ):
		"""
		Return the Excel header for this file. This can be used as input to
		ExcelExporter.
		"""
		import copy
		return copy.copy( self._header )

	def __len__( self ):
		"""
		Return the number of rows in the excel file.
		"""
		return self.sheet.nrows - 1

	def __getitem__( self, value ):
		"""
		Return all values for a specific column
		"""
		return self.sheet.col_values( self.cols[value] )[1:]

	def row( self, rowidx ):
		"""
		Return a specific row in the table.
		"""
		rowidx = rowidx + 1
		data = {}
		for colname, idx in self.cols.items():
			data[colname] = self.sheet.cell( rowx=rowidx, colx=idx ).value
		return data

	def __iter__( self ):
		return ExcelImportIterator( self )


class ExcelImportIterator( ImportIterator ):
	"""
	Iterator object for ExcelImporter
	"""
	def __init__( self, excelimporter ):
		self.excelimporter = excelimporter
		self.rowidx = -1

	def next( self ):
		self.rowidx += 1

		if self.rowidx >= len( self.excelimporter ):
			raise StopIteration

		return self.excelimporter.row( self.rowidx )


# ==============
# CSV Importer
# ==============
class CSVImporter( Importer ):
	"""
	Importer for CSV files.

	Defaults:
		encoding='utf-8'
		dialect=csv.excel

	"""
	def __init__( self, filename=None, **kwargs ):
		"""
		Initialise importer by opening the Excel file and
		reading out a specific sheet.
		"""
		f = open( filename, 'r' )
		self.csvreader = _UnicodeReader( f, **kwargs )

		# Parse header
		i = 0
		self.cols = {}
		header = self.csvreader.next()
		for c in header:
			if isinstance(c, basestring):
				c = c.strip()
			self.cols[c] = i
			i += 1

		# Build dictionary of tabular data
		self._rows = []
		for r in self.csvreader:
			data = {}
			for c, i in self.cols.items():
				try:
					data[c] = r[i]
				except IndexError:
					data[c] = None
			self._rows.append( data )

	def __len__( self ):
		"""
		Return the number of rows in the excel file.
		"""
		return len( self._rows )

	def __getitem__( self, value ):
		"""
		Return all values for a specific column
		"""
		column = []
		for r in self._rows:
			column.append( r[value] )
		return column

	def row( self, rowidx ):
		"""
		Return a specific row in the table.
		"""
		return self._rows[rowidx]

	def __iter__( self ):
		return self._rows.__iter__()


class _UTF8Recoder:
	"""
	Iterator that reads an encoded stream and reencodes the input to UTF - 8
	"""
	def __init__( self, f, encoding ):
		self.reader = codecs.getreader( encoding )( f )

	def __iter__(self):
		return self

	def next( self ):
		return self.reader.next().encode( "utf-8" )


class _UnicodeReader( object ):
	"""
	A CSV reader which will iterate over lines in the CSV file "f",
	which is encoded in the given encoding.
	"""
	def __init__( self, f, dialect=csv.excel, encoding="utf-8", **kwds ):
		f = _UTF8Recoder( f, encoding )
		self.reader = csv.reader( f, dialect=dialect, **kwds )

	def next(self):
		row = self.reader.next()
		return [unicode( s, "utf-8" ) for s in row]

	def __iter__(self):
		return self
