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
from djangoplicity.contacts.models import ContactGroup, Contact, ImportTemplate ,\
    ImportSelector, ImportMapping, ImportGroupMapping, Import
from djangoplicity.contacts.tests.testdata import ContactSetupMixin, ImporterMixin
import os

class ImportTemplateTestCase( ImporterMixin, ContactSetupMixin, TestCase ):
    def _clear_templates( self ):
        ImportGroupMapping.objects.all().delete()
        ImportMapping.objects.all().delete()
        ImportSelector.objects.all().delete()
        ImportTemplate.objects.all().delete()
        Import.objects.all().delete()

    def _import_data( self, rows_data, run_import=True, name='test_import' ):
        excludes = ['id']
        header = filter( lambda x: x not in excludes, rows_data[0].keys() )

        ( template, filename ) = self.create_template( name, header, data=rows_data )
        if run_import:
            template.import_data( filename )
        return ( template, filename )

    def test_missing_column( self ):
        """
        Test importing an excel sheet without a column specified
        """
        # Clean contacts
        self._contacts_setup()
        self._clear_templates()

        rows_data = [
            self.create_contact( 1, extra={ 'country' : 'Misspelled' } ),
            self.create_contact( 4, extra={ 'country' : 'US' } ),
        ]
        del rows_data[0]['position']
        del rows_data[1]['position']

        template, filename = self._import_data( rows_data, run_import=False )
        template.duplicate_handling = 'update'
        template.multiple_duplicates = 'first'

        # Mapping for non existing column
        mapping = ImportMapping( template=template, header='Position', field='position' )
        mapping.save()

        template.import_data( filename )

        c = Contact.objects.get( id=1 )
        self.assertEqual( c.position, "c1.position" )
        self.assertIsNone( c.country ) # Country is specified (so it will be overwritten)
        c = Contact.objects.get( id=4 )
        self.assertEqual( c.position, "" )
        self.assertIsNotNone( c.country )


    def test_multiple_columns( self ):
        """
        Test importing an excel sheet with multiple groups columns
        """
        # Clean contacts
        self._contacts_setup()
        self._clear_templates()

        rows_data = [
            self.create_contact( 1, extra={ 'groups' : 'G2,G3 ', 'position'  : 'G4, G5'} ),
        ]

        template, filename = self._import_data( rows_data, run_import=False )
        template.duplicate_handling = 'update'
        template.multiple_duplicates = 'first'

        # Change position column into a groups column
        mapping = ImportMapping.objects.get( template=template, field='position' )
        mapping.field = 'groups'
        mapping.group_separator = ','
        mapping.save()

        for grp in ContactGroup.objects.all().order_by( 'name' ):
            ImportGroupMapping( mapping=mapping, value=grp.name, group=grp ).save()

        template.import_data( filename )

        c = Contact.objects.get( id=1 )
        self.assertEqual( [x.name for x in c.groups.all()], ['G1', 'G2', 'G3', 'G4', 'G5'] )


    def test_import( self ):
        """
        Test simple import with no duplicate handling etc.
        """
        # Clean contacts
        self._contacts_setup()
        self._clear_templates()

        rows_data = [
            self.create_contact( 4, extra={ 'country' : 'DK', 'skype' : 'c4.skype', 'groups' : 'G1', } ),
            self.create_contact( 5, extra={ 'country' : 'Germany', 'skype' : 'c5.skype', 'groups' : 'G1, G2', } ),
            self.create_contact( 6, extra={ 'country' : 'US', 'skype' : 'c6.skype', 'groups' : 'G2, G3' } ),
            # By default duplicate detection is off, everything is imported
            self.create_contact( 1, extra={ 'country' : 'DK', 'skype' : 'c1.skype-no_dup-detection', 'groups' : 'G5', } ),
        ]

        self._import_data( rows_data )

        for i,data in enumerate(rows_data):
            # Note, data['id'] is not taken into account during import, however,
            # testdata.CONTACTS will create three contacts, so that above contacts
            # will get id 4,5,6 when imported
            c = Contact.objects.get( id=4+i )
            self.assertContact( c, data )

        # C1 shold be untouched
        c = Contact.objects.get( id=1 )
        self.assertEqual( [x.name for x in c.groups.all()], ['G1'] )


    def test_import_baddata( self ):
        """
        Test importing files with invalid data no duplicate handling etc.
        """
        # Clean contacts
        self._contacts_setup()
        self._clear_templates()

        rows_data = [
            self.create_contact( 4, extra={ 'country' : 'DK', 'skype' : 'c4.skype', 'groups' : 'G1', } ),
            self.create_contact( 5, extra={ 'country' : 'DE', 'skype' : 'c5.skype', 'groups' : 'G1, G2', 'email' : 'INVALID' } ),
            self.create_contact( 6, extra={ 'country' : 'INVALID', 'skype' : 'c6.skype', 'groups' : 'G2, G3' } ),
            self.create_contact( 7, extra={ 'country' : 'US', 'skype' : 'c7.skype', 'groups' : 'G2, GINVALID' } ),
        ]

        self._import_data( rows_data )

        c = Contact.objects.get( id=4 )
        self.assertContact( c, rows_data[0] )
        c = Contact.objects.get( id=5 )
        self.assertContact( c, rows_data[1], excludes=['id','email'] )
        self.assertEqual( c.email, 'invalid' )
        c = Contact.objects.get( id=6 )
        self.assertContact( c, rows_data[2], excludes=['id','country'] )
        self.assertIsNone( c.country )
        c = Contact.objects.get( id=7 )
        self.assertContact( c, rows_data[3], excludes=['id','groups'] )
        self.assertEqual( ", ".join( [x.name for x in c.groups.all()] ), 'G2' )


    def test_duplicates( self ):
        """
        Test duplicate detection (ignore/update)
        """
        # Clean contacts
        self._contacts_setup()
        self._clear_templates()

        rows_data = [
            self.create_contact( 1, extra={ 'first_name' : 'notimported', 'groups' : "G3, G4" } ),
            self.create_contact( 4, extra={ 'first_name' : 'imported', 'groups' : "G4, G5" } ),
        ]

        #
        # Ignore duplicates
        #
        template, filename = self._import_data( rows_data, run_import=False )
        template.duplicate_handling = 'ignore'
        template.import_data( filename )

        c = Contact.objects.get( id=1 )
        self.assertEqual( c.first_name, "c1.first_name" )
        self.assertEqual( ", ".join( [x.name for x in c.groups.all()] ), 'G1' )
        c = Contact.objects.get( id=4 )
        self.assertContact( c, rows_data[1] )

        #
        # Update duplicates
        #
        template.duplicate_handling = 'update'
        template.import_data( filename )

        c = Contact.objects.get( id=1 )
        self.assertContact( c, rows_data[0], excludes=['id','groups'] )
        self.assertEqual( ", ".join( [x.name for x in c.groups.all()] ), 'G1, G3, G4' )
        # Just imported, so it will also be updated
        c = Contact.objects.get( id=4 )
        self.assertContact( c, rows_data[1] )
        # A new entry should not have been made.
        self.assertRaises( Contact.DoesNotExist, Contact.objects.get, id=5 )

        #
        # Update groups only
        #
        del rows_data[1]
        rows_data[0]['first_name'] = 'reallynotimported'
        rows_data[0]['groups'] = 'G5'

        template, filename = self._import_data( rows_data, run_import=False, name='test_import2' )
        template.duplicate_handling = 'update_groups'
        template.import_data( filename )

        c = Contact.objects.get( id=1 )
        self.assertEqual( c.first_name, "notimported" )
        self.assertEqual( ", ".join( [x.name for x in c.groups.all()] ), 'G1, G3, G4, G5' )


    def test_multiple_duplicates( self ):
        """
        Test importing with duplicate detection and multiple duplicates
        """
        # Clean contacts
        self._contacts_setup()
        self._clear_templates()

        rows_data = [
            self.create_contact( 4, extra={ 'email' : 'sameemail', 'first_name' : 'dup1' } ),
            self.create_contact( 4, extra={ 'email' : 'sameemail', 'first_name' : 'dup2' } ),
        ]

        # Import
        template, filename = self._import_data( rows_data )

        rows_data = [
            self.create_contact( 4, extra={ 'email' : 'sameemail', 'first_name' : 'dup1-new' } ),
            self.create_contact( 4, extra={ 'email' : 'sameemail', 'first_name' : 'dup2-new' } ),
        ]

        template, filename = self._import_data( rows_data, run_import=False, name='test_import2' )
        template.duplicate_handling = 'update'
        template.multiple_duplicates = 'ignore'
        template.import_data( filename )

        c = Contact.objects.get( id=4 )
        self.assertEqual( c.first_name, "dup1" )
        c = Contact.objects.get( id=5 )
        self.assertEqual( c.first_name, "dup2" )
        self.assertRaises( Contact.DoesNotExist, Contact.objects.get, id=6 )

        template.multiple_duplicates = 'first'
        template.import_data( filename )

        c = Contact.objects.get( id=4 )
        self.assertEqual( c.first_name, "dup2-new" ) # first c will write dup1-new, but then second c will write dup2-new
        c = Contact.objects.get( id=5 )
        self.assertEqual( c.first_name, "dup2" )
        self.assertRaises( Contact.DoesNotExist, Contact.objects.get, id=6 )

        template.multiple_duplicates = 'create_new'
        template.import_data( filename )

        c = Contact.objects.get( id=4 )
        self.assertEqual( c.first_name, "dup2-new" ) # Same as before
        c = Contact.objects.get( id=5 )
        self.assertEqual( c.first_name, "dup2" )  # Same as before
        c = Contact.objects.get( id=6 )
        self.assertEqual( c.first_name, "dup1-new" ) # New created
        c = Contact.objects.get( id=7 )
        self.assertEqual( c.first_name, "dup2-new" ) # New created


    def test_extra_groups( self ):
        """
        Test simple import with no duplicate handling etc.
        """
        # Clean contacts
        self._contacts_setup()
        self._clear_templates()

        rows_data = [
            self.create_contact( 4, extra={ 'groups' : 'G1', } ),
        ]

        template, filename = self._import_data( rows_data, run_import=False, name='test_import1' )
        template.extra_groups.add( ContactGroup.objects.get( name='G5' ) )
        template.import_data( filename )

        c = Contact.objects.get( id=4 )
        self.assertEqual( [x.name for x in c.groups.all()], ['G1','G5'] )

        del rows_data[0]['groups']
        template, filename = self._import_data( rows_data, run_import=False, name='test_import2' )
        template.extra_groups.add( ContactGroup.objects.get( name='G5' ) )
        template.import_data( filename )

        c = Contact.objects.get( id=5 )
        self.assertEqual( [x.name for x in c.groups.all()], ['G5'] )

    def test_frozen_groups( self ):
        """
        Test of frozen groups
        """
        # Clean contacts
        self._contacts_setup()
        self._clear_templates()

        rows_data = [
            self.create_contact( 1, extra={ 'first_name' : 'notupdated', 'groups' : 'G2, G3', } ),
            self.create_contact( 2, extra={ 'first_name' : 'updated', 'groups' : 'G3', } ),
        ]

        template, filename = self._import_data( rows_data, run_import=False, name='test_import1' )
        template.duplicate_handling = 'update'
        template.multiple_duplicates = 'first'
        template.frozen_groups.add( ContactGroup.objects.get( name='G1' ) )
        template.import_data( filename )

        c = Contact.objects.get( id=1 )
        self.assertEqual( c.first_name, 'c1.first_name' )
        self.assertEqual( [x.name for x in c.groups.all()], ['G1', 'G2', 'G3'] ) # Groups are being updated

        c = Contact.objects.get( id=2 )
        self.assertEqual( c.first_name, 'updated' )
        self.assertEqual( [x.name for x in c.groups.all()], ['G2','G3'] )

        self.assertRaises( Contact.DoesNotExist, Contact.objects.get, id=4 )


    def test_selector( self ):
        """
        Test of selectors
        """
        # Clean contacts
        self._contacts_setup()
        self._clear_templates()

        rows_data = [
            self.create_contact( 4, extra={ 'selector' : 'x' } ),
            self.create_contact( 5, extra={ 'selector' : 'X', } ),
        ]

        template, filename = self._import_data( rows_data, run_import=False, name='test_import1' )

        # Mapping is automatically created by test setup, so remove it for selector
        ImportMapping.objects.get( template=template, header=self._field2header( 'selector' ) ).delete()

        # Add as selector instead.
        selector = ImportSelector( template=template, header=self._field2header( 'selector' ), value='x', case_sensitive=True )
        selector.save()

        # Check case-sensitive (lower case)
        template.import_data( filename )

        c = Contact.objects.get( id=4 )
        self.assertContact( c, rows_data[0], excludes=[ 'id', 'selector', ] )
        self.assertRaises( Contact.DoesNotExist, Contact.objects.get, id=5 )

        # Check case-sensitive (upper case)
        selector.case_sensitive = True
        selector.value = 'X'
        selector.save()
        template.import_data( filename )

        c = Contact.objects.get( id=5 )
        self.assertContact( c, rows_data[1], excludes=[ 'id', 'selector', ] )
        self.assertRaises( Contact.DoesNotExist, Contact.objects.get, id=6 )

        # Check case-insensitive (upper case)
        selector.case_sensitive = False
        selector.value = 'X'
        selector.save()
        template.import_data( filename )

        c = Contact.objects.get( id=6 )
        self.assertContact( c, rows_data[0], excludes=[ 'id', 'selector', ] )
        c = Contact.objects.get( id=7 )
        self.assertContact( c, rows_data[1], excludes=[ 'id', 'selector', ] )
        self.assertRaises( Contact.DoesNotExist, Contact.objects.get, id=8 )

        # Check case-insensitive (upper case)
        selector.case_sensitive = False
        selector.value = 'x'
        selector.save()
        template.import_data( filename )

        c = Contact.objects.get( id=8 )
        self.assertContact( c, rows_data[0], excludes=[ 'id', 'selector', ] )
        c = Contact.objects.get( id=9 )
        self.assertContact( c, rows_data[1], excludes=[ 'id', 'selector', ] )
        self.assertRaises( Contact.DoesNotExist, Contact.objects.get, id=10 )
