# Generated by Django 3.0.3 on 2020-03-03 20:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gnt', '0021_auto_20200303_2050'),
    ]

    operations = [
        migrations.AddField(
            model_name='ingredient',
            name='drink_name',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='gnt.User_drink'),
        ),
    ]
