# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-18 08:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('BasicArticle', '0010_articles_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='articles',
            name='image',
            field=models.ImageField(null=True, upload_to='article'),
        ),
    ]
