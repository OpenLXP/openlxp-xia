# Generated by Django 3.2.13 on 2023-05-17 13:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openlxp_xia', '0002_use_xss'),
    ]

    operations = [
        migrations.AddField(
            model_name='xisconfiguration',
            name='xis_api_key',
            field=models.CharField(default='INVALID KEY', help_text='Enter the XIS API Key', max_length=40),
            preserve_default=False,
        ),
    ]
