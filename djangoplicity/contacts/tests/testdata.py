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


#
# Mixin class to automatically create test data
#
class ContactSetupMixin():
    """
    Mixin object to create a number of contacts, extra fields, groups and countries.

    Will additionally clear the fields on start
    """

    def setUp( self ):
        self._contacts_setup()

    def _contacts_setup( self ):
        """
        Setup test data
        """
        from djangoplicity.contacts.models import Contact, ContactGroup, Field, Country

        Contact.objects.all().delete()
        ContactGroup.objects.all().delete()
        Field.objects.all().delete()
        Country.objects.all().delete()

        self.fields = []
        self.contactgroups = []
        self.countrys = []
        self.contacts = []

        for data_list, klass in [ ( EXTRA_FIELDS, Field ), ( COUNTRIES, Country ), ( GROUPS, ContactGroup ), ( CONTACTS, Contact ) ]:
            listattr = "%ss" % klass.__name__.lower()

            for data in data_list:
                obj = klass( **data )
                obj.save()
                getattr( self, listattr ).append( obj )

        for i, c in enumerate( self.contacts ):
            c.country = self.countrys[i]
            c.save()
            c.groups.add( self.contactgroups[i] )


    @staticmethod
    def create_contact( num, extra = {} ):
        data = {
            'id' : num,
            'first_name' : 'c%s.' % num,
            'last_name' : 'c%s.' % num,
            'title' : 'c%s.' % num,
            'position' : 'c%s.' % num,
            'organisation' : 'c%s.' % num,
            'department' : 'c%s.' % num,
            'street_1' : 'c%s.' % num,
            'street_2' : 'c%s.' % num,
            'city' : 'c%s.' % num,
            'phone' : 'c%s.' % num,
            'website' : 'c%s.' % num,
            'social' : 'c%s.' % num,
            'email' : 'c%s@' % num,
            #'groups' : 'c%s.' % num,
            #'country' : 'c%s.' % num,

            #'zip' : 'c%s.' % num,
            #'postal_code' : 'c%s.' % num,
            #'state' : 'c%s.' % num,
        }

        newdata = {}
        for k,v in data.items():
            if k == 'id':
                newdata[k] = v
            else:
                newdata[k] = "%s%s" % ( v, k )

        newdata.update( extra )
        return newdata


class ImporterMixin( object ):
    """
    Mixin object to make writing excel test files easy.
    """
    files = []

    def tearDown( self ):
        """ Make sure all files are removed """
        import os
        for f in self.files:
            try:
                os.remove(f)
            except OSError:
                pass

    def _new_file( self, suffix, text=False ):
        """
        Create a new temporary file and return the path
        """
        import tempfile
        ( handle, path ) = tempfile.mkstemp( suffix=suffix, text=text )
        self.files.append( path )
        return path

    def _field2header( self, val ):
        """
        To ensure that headers doesn't match exactly with fields,
        we change them using a simple non-destructive transformation
        which can be undone with header2field().
        """
        return "TEST-%s" % val.replace( "_", " " ).title()

    def _header2field( self, val ):
        return val.lower().replace( " ", "_" )[5:]

    def _contactgroup2group( self, val ):
        """
        To ensure that groups doesn't match exactly with group names,
        we change them using a simple non-destructive transformation
        which can be undone with group2contactgroup().
        """
        return "TEST-%s" % val

    def group2contactgroup( self, val ):
        return "TEST-%s" % val[5:]

    def create_excel_file( self, header, rows=[], data=[], fix_header=True ):
        """
        Write an excel file to a temporary file
        """
        from djangoplicity.contacts.exporter import ExcelExporter

        filename = self._new_file( ".xls" )
        exporter = ExcelExporter( filename_or_stream=filename, header=[( self._field2header( h ) if fix_header else h, None ) for h in header] )

        if rows:
            exporter.writerows( rows )
        elif data:
            for row in data:
                # Change keys to that of the header
                rowdata = {}
                for k,v in row.items():
                    if k == 'groups' and fix_header:
                        v = ", ".join( [self._contactgroup2group( x.strip() ) for x in v.split(",")] )
                    rowdata[self._field2header( k )  if fix_header else k] = v
                exporter.writedata( rowdata )

        exporter.save()

        return filename

    def create_template( self, name, header, rows=[], data=[] ):
        """
        Create an import template with correct mapping and write excel test
        file for testing the import template
        """
        # Create template
        from djangoplicity.contacts.models import ImportTemplate, ImportMapping, ContactGroup, ImportGroupMapping
        tpl = ImportTemplate(
            name=name,
            duplicate_handling='none',
            multiple_duplicates='ignore',
            tag_import=False,
        )
        tpl.save()

        for h in header:
            # Setup field mapping
            mapping = ImportMapping( template=tpl, header=self._field2header( h ), field=h )
            if h == 'groups':
                mapping.group_separator = ','
            mapping.save()

            # Setup group mapping
            if h == 'groups':
                for grp in ContactGroup.objects.all().order_by( 'name' ):
                    ImportGroupMapping( mapping=mapping, value=self._contactgroup2group( grp.name ), group=grp ).save()


        # Create excel file and return template + filename
        return ( tpl, self.create_excel_file( header, rows=rows, data=data ) )

    def assertContact( self, c, data, excludes=['id'] ):
        """
        Test if imported data corresponds to imported contact
        """
        for k, v in  data.items():
            if k not in excludes + ['groups', 'country', 'skype']:
                self.assertEqual( getattr( c, k ), v )

        if 'country' in data and 'country' not in excludes:
            if len( data['country'] ) == 2:
                self.assertEqual( c.country.iso_code, data['country'] )
            else:
                self.assertEqual( c.country.name, data['country'] )
        if 'groups' in data and 'groups' not in excludes:
            self.assertEqual( ", ".join( [x.name for x in c.groups.all().order_by( 'name' )] ), data['groups'] )
        if 'skype' in data and 'skype' not in excludes:
            self.assertEqual( c.get_extra_field( 'skype' ), data['skype'] )


#
# Data
#
EXTRA_FIELDS = [
    {'slug' : 'skype', 'name' : 'skype', 'blank' : True },
    {'slug' : 'email_2', 'name' : 'Second email', 'blank' : True },
]

GROUPS = [
    { 'name' : 'G1', 'order' : 1, },
    { 'name' : 'G2', 'order' : 2, },
    { 'name' : 'G3', 'order' : 3, },
    { 'name' : 'G4', 'order' : 4, },
    { 'name' : 'G5', 'order' : 5, },
]

COUNTRIES = [
    { 'name' : 'Germany', 'iso_code' : 'DE', 'zip_after_city' : False },
    { 'name' : 'Denmark', 'iso_code' : 'DK', 'zip_after_city' : False },
    { 'name' : 'USA', 'iso_code' : 'US', 'zip_after_city' : True },
]

CONTACTS = [
    ContactSetupMixin.create_contact(1),
    ContactSetupMixin.create_contact(2),
    ContactSetupMixin.create_contact(3),
]
