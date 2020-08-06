# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import djangoplicity.translation.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0002_auto_20150327_1553'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='email',
            field=models.EmailField(max_length=254, blank=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='language',
            field=djangoplicity.translation.fields.LanguageField(max_length=7, null=True, verbose_name='Language', blank=True),
        ),
    ]
