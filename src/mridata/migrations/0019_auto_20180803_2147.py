# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2018-08-04 04:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mridata', '0018_auto_20180803_1747'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ismrmrddata',
            name='ismrmrd_file',
            field=models.FileField(blank=True, upload_to='uploads/'),
        ),
    ]