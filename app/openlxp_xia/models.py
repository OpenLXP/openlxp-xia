import json
import logging
import os
import uuid

import boto3
from django.db import models
from django.forms import ValidationError
from django.urls import reverse
from model_utils.models import TimeStampedModel

logger = logging.getLogger('dict_config_logger')


class XIAConfiguration(TimeStampedModel):
    """Model for XIA Configuration """
    publisher = models.CharField(max_length=200,
                                 help_text='Enter the publisher name')
    source_metadata_schema = models.CharField(max_length=200,
                                              help_text='Enter the JKO '
                                                        'schema file')
    source_target_mapping = models.CharField(max_length=200,
                                             help_text='Enter the schema '
                                                       'file to map '
                                                       'target.')
    target_metadata_schema = models.CharField(max_length=200,
                                              help_text='Enter the target '
                                                        'schema file to '
                                                        'validate from.')
    source_file = models.FileField(help_text='Upload the source '
                                             'file')

    def get_absolute_url(self):
        """ URL for displaying individual model records."""
        return reverse('Configuration-detail', args=[str(self.id)])

    def __str__(self):
        """String for representing the Model object."""
        return f'{self.id}'

    def save(self, *args, **kwargs):
        # Deleting the corresponding existing value to overwrite
        MetadataFieldOverwrite.objects.all().delete()
        # get required columns list from schema files
        s3 = boto3.resource('s3')
        bucket_name = os.environ.get('BUCKET_NAME')
        # Read json file and store as a dictionary for processing
        mapping_path = s3.Object(bucket_name, self.source_target_mapping)
        mapping_content = mapping_path.get()['Body'].read().decode('utf-8')
        mapping = json.loads(mapping_content)

        # Read json file and store as a dictionary for processing
        target_path = s3.Object(bucket_name, self.target_metadata_schema)
        target_content = target_path.get()['Body'].read().decode('utf-8')
        target = json.loads(target_content)

        # saving required column values to be overwritten
        for section in target:
            for key, val in target[section].items():
                if val == 'Required':
                    if section in mapping and key in mapping[section]:
                        metadata_field_overwrite = MetadataFieldOverwrite()
                        metadata_field_overwrite.field_name = \
                            mapping[section][key]
                        metadata_field_overwrite.save()
                    else:
                        logger.error("Mapping for required value " +
                                     section + "." + key +
                                     " not found in schema mapping")

        if not self.pk and XIAConfiguration.objects.exists():
            raise ValidationError('There can be only one XIAConfiguration '
                                  'instance')
        return super(XIAConfiguration, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Deleting the corresponding existing value to overwrite
        metadata_fields = MetadataFieldOverwrite.objects.all()
        metadata_fields.delete()
        return super(XIAConfiguration, self).delete(*args, **kwargs)


class XISConfiguration(TimeStampedModel):
    """Model for XIS Configuration """

    xis_metadata_api_endpoint = models.CharField(
        help_text='Enter the XIS Metadata Ledger API endpoint',
        max_length=200
    )

    xis_supplemental_api_endpoint = models.CharField(
        help_text='Enter the XIS Supplemental Ledger API endpoint',
        max_length=200
    )

    def save(self, *args, **kwargs):
        if not self.pk and XISConfiguration.objects.exists():
            raise ValidationError('There can be only one XISConfiguration '
                                  'instance')
        return super(XISConfiguration, self).save(*args, **kwargs)


class MetadataLedger(TimeStampedModel):
    """Model for MetadataLedger """

    METADATA_VALIDATION_CHOICES = [('Y', 'Yes'), ('N', 'No')]
    RECORD_ACTIVATION_STATUS_CHOICES = [('Active', 'A'), ('Inactive', 'I')]
    RECORD_TRANSMISSION_STATUS_CHOICES = [('Successful', 'S'), ('Failed', 'F'),
                                          ('Pending', 'P'), ('Ready', 'R')]

    metadata_record_inactivation_date = models.DateTimeField(blank=True,
                                                             null=True)
    metadata_record_uuid = models.UUIDField(primary_key=True,
                                            default=uuid.uuid4, editable=False)
    record_lifecycle_status = models.CharField(
        max_length=10, blank=True, choices=RECORD_ACTIVATION_STATUS_CHOICES)
    source_metadata = models.JSONField(blank=True)
    source_metadata_extraction_date = models.DateTimeField(auto_now_add=True)
    source_metadata_hash = models.CharField(max_length=200)
    source_metadata_key = models.TextField()
    source_metadata_key_hash = models.CharField(max_length=200)
    source_metadata_transformation_date = models.DateTimeField(blank=True,
                                                               null=True)
    source_metadata_validation_date = models.DateTimeField(blank=True,
                                                           null=True)
    source_metadata_validation_status = models.CharField(
        max_length=10, blank=True, choices=METADATA_VALIDATION_CHOICES)
    target_metadata = models.JSONField(default=dict)
    target_metadata_hash = models.CharField(max_length=200)
    target_metadata_key = models.TextField()
    target_metadata_key_hash = models.CharField(max_length=200)
    target_metadata_transmission_date = models.DateTimeField(blank=True,
                                                             null=True)
    target_metadata_transmission_status = models.CharField(
        max_length=10, blank=True, default='Ready',
        choices=RECORD_TRANSMISSION_STATUS_CHOICES)
    target_metadata_transmission_status_code = models.IntegerField(blank=True,
                                                                   null=True)
    target_metadata_validation_date = models.DateTimeField(blank=True,
                                                           null=True)
    target_metadata_validation_status = models.CharField(
        max_length=10, blank=True, choices=METADATA_VALIDATION_CHOICES)


class SupplementalLedger(TimeStampedModel):
    """Model for Supplemental Metadata """

    RECORD_ACTIVATION_STATUS_CHOICES = [('Active', 'A'), ('Inactive', 'I')]
    RECORD_TRANSMISSION_STATUS_CHOICES = [('Successful', 'S'), ('Failed', 'F'),
                                          ('Pending', 'P'), ('Ready', 'R')]

    metadata_record_inactivation_date = models.DateTimeField(blank=True,
                                                             null=True)
    metadata_record_uuid = models.UUIDField(primary_key=True,
                                            default=uuid.uuid4, editable=False)
    record_lifecycle_status = models.CharField(
        max_length=10, blank=True, choices=RECORD_ACTIVATION_STATUS_CHOICES)
    supplemental_metadata = models.JSONField(blank=True)
    supplemental_metadata_extraction_date = models.DateTimeField(
        auto_now_add=True)
    supplemental_metadata_hash = models.CharField(max_length=200)
    supplemental_metadata_key = models.TextField()
    supplemental_metadata_key_hash = models.CharField(max_length=200)
    supplemental_metadata_transformation_date = models.DateTimeField(
        blank=True, null=True)
    supplemental_metadata_validation_date = models.DateTimeField(
        blank=True, null=True)
    supplemental_metadata_transmission_date = models.DateTimeField(
        blank=True, null=True)
    supplemental_metadata_transmission_status = models.CharField(
        max_length=10, blank=True, default='Ready',
        choices=RECORD_TRANSMISSION_STATUS_CHOICES)
    supplemental_metadata_transmission_status_code = models.IntegerField(
        blank=True, null=True)


class MetadataFieldOverwrite(TimeStampedModel):
    """Model for taking list of fields name and it's values for overwriting
    field values in Source metadata"""

    COLOR_CHOICES = (
        ('datetime', 'DATETIME'),
        ('int', 'INTEGER'),
        ('char', 'CHARACTER'),
        ('bool', 'BOOLEAN'),
        ('txt', 'TEXT'),
    )

    field_name = models.CharField(max_length=200)
    field_type = models.CharField(max_length=200, choices=COLOR_CHOICES,
                                  null=True)
    field_value = models.CharField(max_length=200, null=True)
    overwrite = models.BooleanField(default=False)

    def __str__(self):
        """String for representing the Model object."""
        return f'{self.id}'

    def save(self, *args, **kwargs):
        return super(MetadataFieldOverwrite, self).save(*args, **kwargs)
