# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.files.storage
import djangoplicity.contacts.models
import dirtyfields.dirtyfields


class Migration(migrations.Migration):

    dependencies = [
        ('actions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('first_name', models.CharField(max_length=255, blank=True)),
                ('last_name', models.CharField(max_length=255, blank=True)),
                ('title', models.CharField(db_index=True, max_length=50, blank=True)),
                ('position', models.CharField(max_length=255, blank=True)),
                ('organisation', models.CharField(max_length=255, blank=True)),
                ('department', models.CharField(max_length=255, blank=True)),
                ('street_1', models.CharField(max_length=255, blank=True)),
                ('street_2', models.CharField(max_length=255, blank=True)),
                ('city', models.CharField(help_text=b'Including postal code, city and state.', max_length=255, blank=True)),
                ('phone', models.CharField(max_length=255, blank=True)),
                ('website', models.CharField(max_length=255, verbose_name=b'Website', blank=True)),
                ('social', models.CharField(max_length=255, verbose_name=b'Social media', blank=True)),
                ('email', models.EmailField(max_length=75, blank=True)),
                ('language', models.CharField(blank=True, max_length=5, null=True, verbose_name='Language', choices=[(b'en', b'English'), (b'en-au', b'English/Australia'), (b'en-gb', b'English/United Kingdom'), (b'en-ie', b'English/Ireland'), (b'en-us', b'English/US'), (b'sq', b'Albanian'), (b'cs', b'Czech'), (b'da', b'Danish'), (b'nl', b'Dutch'), (b'nl-be', b'Dutch/Belgium'), (b'fi', b'Finnish'), (b'fr', b'French'), (b'fr-be', b'French/Belgium'), (b'fr-ch', b'French/Switzerland'), (b'de', b'German'), (b'de-at', b'German/Austria'), (b'de-be', b'German/Belgium'), (b'de-ch', b'German/Switzerland'), (b'is', b'Icelandic'), (b'it', b'Italian'), (b'it-ch', b'Italian/Switzerland'), (b'no', b'Norwegian'), (b'pl', b'Polish'), (b'pt-br', b'Portuguese/Brazil'), (b'pt', b'Portuguese/Portugal'), (b'ru', b'Russian'), (b'es', b'Spanish'), (b'es-cl', b'Spanish/Chile'), (b'sr', b'Serbian'), (b'sv', b'Swedish'), (b'tr', b'Turkish'), (b'uk', b'Ukrainian')])),
                ('group_order', models.PositiveIntegerField(null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['last_name'],
            },
            bases=(dirtyfields.dirtyfields.DirtyFieldsMixin, models.Model),
        ),
        migrations.CreateModel(
            name='ContactField',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(db_index=True, max_length=255, blank=True)),
                ('contact', models.ForeignKey(to='contacts.Contact', on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContactGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, blank=True)),
                ('order', models.PositiveIntegerField(null=True, blank=True)),
            ],
            options={
                'ordering': ('name',),
            },
            bases=(dirtyfields.dirtyfields.DirtyFieldsMixin, models.Model),
        ),
        migrations.CreateModel(
            name='ContactGroupAction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('on_event', models.CharField(db_index=True, max_length=50, choices=[(b'contact_added', b'Contact added to group'), (b'contact_removed', b'Contact removed from group'), (b'contact_updated', b'Contact updated'), (b'periodic_5min', b'Every 5 minutes'), (b'periodic_30min', b'Every 30 minutes'), (b'periodic_1hr', b'Every hour'), (b'periodic_6hr', b'Every 6 hours'), (b'periodic_24hr', b'Every day')])),
                ('action', models.ForeignKey(to='actions.Action', on_delete=django.db.models.deletion.CASCADE)),
                ('group', models.ForeignKey(to='contacts.ContactGroup', on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=40, db_index=True)),
                ('iso_code', models.CharField(max_length=5, verbose_name='ISO code', blank=True)),
                ('dialing_code', models.CharField(max_length=10, blank=True)),
                ('zip_after_city', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name_plural': 'countries',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CountryGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(db_index=True, max_length=255, blank=True)),
            ],
            options={
                'ordering': ('category__name', 'name'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Deduplication',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default=b'new', help_text=b'', max_length=20, choices=[(b'new', b'New'), (b'processing', b'Processing'), (b'review', b'Review')])),
                ('last_deduplication', models.DateTimeField(null=True)),
                ('duplicate_contacts', models.TextField(blank=True)),
                ('deduplicated_contacts', models.TextField(blank=True)),
                ('max_display', models.IntegerField(default=25, help_text=b'Maximum number of duplicates to display at once.')),
                ('min_score_display', models.FloatField(default=0.7, help_text=b'Only display duplicates with score above this score.')),
                ('groups', models.ManyToManyField(to='contacts.ContactGroup', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.SlugField(unique=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('blank', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, blank=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name_plural': 'group categories',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Import',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('data_file', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'/Users/rino/dev/eso17/tmp/contacts_import'), upload_to=djangoplicity.contacts.models.handle_uploaded_file)),
                ('status', models.CharField(default=b'new', help_text=b'', max_length=20, choices=[(b'new', b'New'), (b'processing', b'Processing'), (b'review', b'Review')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('last_deduplication', models.DateTimeField(null=True)),
                ('imported_contacts', models.TextField(blank=True)),
                ('duplicate_contacts', models.TextField(blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ImportGroupMapping',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(max_length=255)),
                ('group', models.ForeignKey(to='contacts.ContactGroup', on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ImportMapping',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('header', models.CharField(max_length=255)),
                ('field', models.SlugField(max_length=255)),
                ('group_separator', models.CharField(default=b'', max_length=20, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ImportSelector',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('header', models.CharField(max_length=255)),
                ('value', models.CharField(max_length=255)),
                ('case_sensitive', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ImportTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('duplicate_handling', models.CharField(default=b'smart', help_text=b'', max_length=20, choices=[(b'smart', b'Detect duplicates and wait for review')])),
                ('tag_import', models.BooleanField(default=True, help_text=b'Create a contact group for this import.')),
                ('extra_groups', models.ManyToManyField(to='contacts.ContactGroup', blank=True)),
                ('frozen_groups', models.ManyToManyField(help_text=b'Contacts belonging to these groups will not be updated.', related_name='importtemplate_frozen_set', to='contacts.ContactGroup', blank=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Label',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('paper', models.CharField(max_length=255, choices=[(b'a4-l7163', b'A4 (L7163 - 99.1x38.1)'), (b'us-letter-5162', b'US Letter (5162 - 102x34)'), (b'a4-l7165', b'A4 (L7165 - 99.1x67.7)')])),
                ('repeat', models.PositiveIntegerField(default=1)),
                ('style', models.TextField(blank=True)),
                ('template', models.TextField(blank=True)),
                ('enabled', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PostalZone',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='importselector',
            name='template',
            field=models.ForeignKey(to='contacts.ImportTemplate', on_delete=django.db.models.deletion.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='importmapping',
            name='template',
            field=models.ForeignKey(to='contacts.ImportTemplate', on_delete=django.db.models.deletion.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='importgroupmapping',
            name='mapping',
            field=models.ForeignKey(to='contacts.ImportMapping', on_delete=django.db.models.deletion.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='import',
            name='template',
            field=models.ForeignKey(to='contacts.ImportTemplate', on_delete=django.db.models.deletion.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='countrygroup',
            name='category',
            field=models.ForeignKey(blank=True, to='contacts.GroupCategory', null=True, on_delete=django.db.models.deletion.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='country',
            name='groups',
            field=models.ManyToManyField(to='contacts.CountryGroup', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='country',
            name='postal_zone',
            field=models.ForeignKey(blank=True, to='contacts.PostalZone', null=True, on_delete=django.db.models.deletion.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contactgroup',
            name='category',
            field=models.ForeignKey(blank=True, to='contacts.GroupCategory', null=True, on_delete=django.db.models.deletion.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contactfield',
            name='field',
            field=models.ForeignKey(to='contacts.Field', on_delete=django.db.models.deletion.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='contactfield',
            unique_together=set([('field', 'contact')]),
        ),
        migrations.AddField(
            model_name='contact',
            name='country',
            field=models.ForeignKey(blank=True, to='contacts.Country', null=True, on_delete=django.db.models.deletion.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contact',
            name='extra_fields',
            field=models.ManyToManyField(to='contacts.Field', through='contacts.ContactField'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contact',
            name='groups',
            field=models.ManyToManyField(to='contacts.ContactGroup', blank=True),
            preserve_default=True,
        ),
    ]
