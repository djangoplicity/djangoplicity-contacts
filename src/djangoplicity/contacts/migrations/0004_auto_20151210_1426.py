# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0003_auto_20151104_1436'),
    ]

    operations = [
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200, verbose_name=b'Region/State name', db_index=True)),
                ('local_name', models.CharField(max_length=200, verbose_name=b'Region/State name in the local language')),
                ('code', models.CharField(max_length=200, db_index=True)),
                ('country', models.ForeignKey(to='contacts.Country')),
            ],
        ),
        migrations.AddField(
            model_name='contact',
            name='region',
            field=models.ForeignKey(blank=True, to='contacts.Region', null=True),
        ),
    ]
