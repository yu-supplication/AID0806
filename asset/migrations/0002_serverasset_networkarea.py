# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-08-05 01:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asset', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='serverasset',
            name='networkarea',
            field=models.CharField(blank=True, max_length=20, verbose_name='\u533a\u57df'),
        ),
    ]