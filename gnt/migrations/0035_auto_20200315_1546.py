# Generated by Django 3.0.3 on 2020-03-15 15:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gnt', '0034_auto_20200315_1534'),
    ]

    operations = [
        migrations.RenameField(
            model_name='friend',
            old_name='profile_FK',
            new_name='friend1',
        ),
        migrations.RenameField(
            model_name='friend',
            old_name='friend_FK',
            new_name='friend2',
        ),
        migrations.RenameField(
            model_name='friendrequest',
            old_name='profile_FK',
            new_name='requestee',
        ),
        migrations.RenameField(
            model_name='friendrequest',
            old_name='request_FK',
            new_name='requestor',
        ),
    ]