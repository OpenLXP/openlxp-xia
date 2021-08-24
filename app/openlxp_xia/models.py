import uuid

from django.db import models
from django.forms import ValidationError
from django.urls import reverse
from model_utils.models import TimeStampedModel


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
        if not self.pk and XIAConfiguration.objects.exists():
            raise ValidationError('There can be only one XIAConfiguration '
                                  'instance')
        return super(XIAConfiguration, self).save(*args, **kwargs)


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
    field_type = models.CharField(max_length=200, choices=COLOR_CHOICES)
    field_value = models.CharField(max_length=200)
    overwrite = models.BooleanField()

    def __str__(self):
        """String for representing the Model object."""
        return f'{self.id}'

    def save(self, *args, **kwargs):
        return super(MetadataFieldOverwrite, self).save(*args, **kwargs)
