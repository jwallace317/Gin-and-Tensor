# Generated by Django 3.0.3 on 2020-03-03 19:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gnt', '0016_auto_20200302_1131'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='bio',
            field=models.CharField(default='insert bio here', max_length=250),
        ),
    ]