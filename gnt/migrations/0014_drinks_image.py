# Generated by Django 3.0.3 on 2020-03-02 16:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gnt', '0013_friend_request'),
    ]

    operations = [
        migrations.AddField(
            model_name='drinks',
            name='image',
            field=models.ImageField(default=None, upload_to='drink_pics'),
        ),
    ]
