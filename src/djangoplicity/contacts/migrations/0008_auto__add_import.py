# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Import'
        db.create_table('contacts_import', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('template', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contacts.ImportTemplate'])),
            ('data_file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('imported', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('contacts', ['Import'])


    def backwards(self, orm):
        
        # Deleting model 'Import'
        db.delete_table('contacts_import')


    models = {
        'actions.action': {
            'Meta': {'ordering': "['name']", 'object_name': 'Action'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'plugin': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'contacts.contact': {
            'Meta': {'ordering': "['last_name']", 'object_name': 'Contact'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contacts.Country']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'department': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'extra_fields': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['contacts.Field']", 'through': "orm['contacts.ContactField']", 'symmetrical': 'False'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['contacts.ContactGroup']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'organisation': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'position': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'social': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'street_1': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'street_2': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'blank': 'True'}),
            'website': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'contacts.contactfield': {
            'Meta': {'unique_together': "(('field', 'contact'),)", 'object_name': 'ContactField'},
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contacts.Contact']"}),
            'field': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contacts.Field']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '255', 'blank': 'True'})
        },
        'contacts.contactgroup': {
            'Meta': {'ordering': "('name',)", 'object_name': 'ContactGroup'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contacts.GroupCategory']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'contacts.contactgroupaction': {
            'Meta': {'object_name': 'ContactGroupAction'},
            'action': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['actions.Action']"}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contacts.ContactGroup']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'on_event': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'contacts.country': {
            'Meta': {'ordering': "['name']", 'object_name': 'Country'},
            'dialing_code': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['contacts.CountryGroup']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'iso_code': ('django.db.models.fields.CharField', [], {'max_length': '5', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'postal_zone': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contacts.PostalZone']", 'null': 'True', 'blank': 'True'}),
            'zip_after_city': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'contacts.countrygroup': {
            'Meta': {'ordering': "('category__name', 'name')", 'object_name': 'CountryGroup'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contacts.GroupCategory']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '255', 'blank': 'True'})
        },
        'contacts.field': {
            'Meta': {'ordering': "['name']", 'object_name': 'Field'},
            'blank': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'contacts.groupcategory': {
            'Meta': {'ordering': "('name',)", 'object_name': 'GroupCategory'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'contacts.import': {
            'Meta': {'object_name': 'Import'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contacts.ImportTemplate']"})
        },
        'contacts.importgroupmapping': {
            'Meta': {'object_name': 'ImportGroupMapping'},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contacts.ContactGroup']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapping': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contacts.ImportMapping']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'contacts.importmapping': {
            'Meta': {'object_name': 'ImportMapping'},
            'field': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'group_separator': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '20', 'blank': 'True'}),
            'header': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contacts.ImportTemplate']"})
        },
        'contacts.importselector': {
            'Meta': {'object_name': 'ImportSelector'},
            'case_sensitive': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'header': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contacts.ImportTemplate']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'contacts.importtemplate': {
            'Meta': {'ordering': "['name']", 'object_name': 'ImportTemplate'},
            'duplicate_handling': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'extra_groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['contacts.ContactGroup']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'multiple_duplicates': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'tag_import': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'contacts.label': {
            'Meta': {'ordering': "['name']", 'object_name': 'Label'},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'paper': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'repeat': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'style': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'template': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'contacts.postalzone': {
            'Meta': {'ordering': "['name']", 'object_name': 'PostalZone'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['contacts']