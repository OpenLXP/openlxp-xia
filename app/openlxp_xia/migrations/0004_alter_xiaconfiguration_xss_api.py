# Generated by Django 3.2.13 on 2023-05-17 20:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openlxp_xia', '0003_xisconfiguration_xis_api_key'),
    ]

    operations = [
        migrations.AlterField(
            model_name='xiaconfiguration',
            name='xss_api',
            field=models.CharField(help_text='Enter the XSS API', max_length=200),
        ),
    ]
