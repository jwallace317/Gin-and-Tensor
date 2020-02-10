# Generated by Django 3.0.2 on 2020-02-09 21:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gnt', '0006_auto_20200209_1633'),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile_to_drink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('drink_FK', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='gnt.Drinks')),
                ('profile_FK', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='gnt.Profile')),
            ],
        ),
    ]