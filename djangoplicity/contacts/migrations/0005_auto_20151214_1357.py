# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0004_auto_20151210_1426'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='region',
            options={'ordering': ['country', 'name']},
        ),
        migrations.AddField(
            model_name='contact',
            name='tax_code',
            field=models.CharField(help_text='Tax Code for Argentina, Brazil, Paraguay, Peru (CUIT/CPF/RUC)', max_length=20, verbose_name='Tax Code', blank=True),
        ),
    ]
