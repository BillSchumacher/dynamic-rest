# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-08-08 13:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tests", "0003_auto_20160401_1656"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_dead",
            field=models.NullBooleanField(default=False),
        ),
    ]
