import logging
import uuid

import requests
from django.db import models
from django.forms import ValidationError
from django.core.validators import RegexValidator
from django.urls import reverse
from django.utils import timezone
from openlxp_xia.management.utils.model_help import confusable_homoglyphs_check
from openlxp_xia.management.utils.model_help import bleach_data_to_json
from model_utils.models import TimeStampedModel

logger = logging.getLogger('dict_config_logger')


rcheck = (r'(?!(\A( \x09\x0A\x0D\x20-\x7E # ASCII '
          r'| \xC2-\xDF # non-overlong 2-byte '
          r'| \xE0\xA0-\xBF # excluding overlongs '
          r'| \xE1-\xEC\xEE\xEF{2} # straight 3-byte '
          r'| \xED\x80-\x9F # excluding surrogates '
          r'| \xF0\x90-\xBF{2} # planes 1-3 '
          r'| \xF1-\xF3{3} # planes 4-15 '
          r'| \xF4\x80-\x8F{2} # plane 16 )*\Z))')


class XIAConfiguration(TimeStampedModel):
    """Model for XIA Configuration """
    publisher = models.CharField(max_length=200,
                                 help_text='Enter the publisher name')
    xss_api = models.CharField(help_text='Enter the XSS API', max_length=200)
    source_metadata_schema = models.CharField(max_length=200,
                                              help_text='Enter the '
                                                        'schema name/IRI')
    target_metadata_schema = models.CharField(max_length=200,
                                              help_text='Enter the target '
                                                        'schema name/IRI to '
                                                        'validate from.')
    source_file = models.FileField(help_text='Upload the source '
                                             'file')

    def get_absolute_url(self):
        """ URL for displaying individual model records."""
        return reverse('Configuration-detail', args=[str(self.id)])

    def __str__(self):
        """String for representing the Model object."""
        return f'{self.id}'

    def field_overwrite(self):
        # Deleting the corresponding existing value to overwrite
        MetadataFieldOverwrite.objects.all().delete()
        # get required columns list from schema files
        conf = self.xss_api
        # Read json file and store as a dictionary for processing
        request_path = conf
        if (self.target_metadata_schema.startswith('xss:')):
            request_path += 'schemas/?iri=' + self.target_metadata_schema
            conf += 'mappings/?targetIRI=' + self.target_metadata_schema
        else:
            request_path += 'schemas/?name=' + self.target_metadata_schema
            conf += 'mappings/?targetName=' + self.target_metadata_schema
        schema = requests.get(request_path, verify=False)
        target = schema.json()['schema']

        # Read json file and store as a dictionary for processing
        request_path = conf
        if (self.source_metadata_schema.startswith('xss:')):
            request_path += '&sourceIRI=' + self.source_metadata_schema
        else:
            request_path += '&sourceName=' + self.source_metadata_schema
        schema = requests.get(request_path, verify=False)
        mapping = schema.json()['schema_mapping']

        # saving required column values to be overwritten
        for section in target:
            for key, val in target[section].items():
                if "use" in val:
                    if val["use"] == 'Required':
                        if section in mapping and key in mapping[section]:
                            metadata_field_overwrite = MetadataFieldOverwrite()
                            metadata_field_overwrite.field_name = \
                                mapping[section][key]
                            # assigning default value for datatype field
                            # for metadata
                            metadata_field_overwrite.field_type = "str"
                            # assigning datatype field from schema
                            if "data_type" in val:
                                metadata_field_overwrite. \
                                    field_type = val["data_type"]
                            # logging if datatype for field not present in
                            # schema
                            else:
                                logger.warning("Datatype for required value " +
                                               section + "." + key +
                                               " not found in schema mapping")
                            metadata_field_overwrite.save()
                        # logging is mapping for metadata not present in schema
                        else:
                            logger.error("Mapping for required value " +
                                         section + "." + key +
                                         " not found in schema mapping")

    def save(self, *args, **kwargs):
        # Retrieve list of field required to be overwritten
        self.field_overwrite()
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

    xis_api_key = models.CharField(
        help_text="Enter the XIS API Key",
        max_length=128
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
    source_metadata = models.JSONField(blank=True,
                                       validators=[RegexValidator(regex=rcheck,
                                                                  message="The"
                                                                  " Wrong "
                                                                  "Format "
                                                                  "Entered")])
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

    def save(self, *args, **kwargs):
        source_data = self.source_metadata
        # Checking for confusable hologlyphs 
        data_checked = confusable_homoglyphs_check(source_data)
        if not data_checked:
            # If data check failed setting metadata to inactive
            self.record_lifecycle_status = "Inactive"
            self.metadata_record_inactivation_date=timezone.now()
        # cleaning metadata using bleach 
        self.source_metadata = bleach_data_to_json(source_data)
        return super(MetadataLedger, self).save(*args, **kwargs)


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
    supplemental_metadata = models.JSONField(blank=True,
                                             validators=[RegexValidator
                                                         (regex=rcheck,
                                                          message="The"
                                                                  " Wrong "
                                                                  "Format "
                                                                  "Entered")])
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

    def save(self, *args, **kwargs):
        source_data = self.supplemental_metadata
        # Checking for confusable hologlyphs 
        data_checked = confusable_homoglyphs_check(source_data)
        if not data_checked:
            # If data check failed setting metadata to inactive
            self.record_lifecycle_status = "Inactive"
            self.metadata_record_inactivation_date=timezone.now()
        # cleaning metadata using bleach 
        self.source_metadata = bleach_data_to_json(source_data)
        return super(SupplementalLedger, self).save(*args, **kwargs)


class MetadataFieldOverwrite(TimeStampedModel):
    """Model for taking list of fields name and it's values for overwriting
    field values in Source metadata"""

    DATATYPE_CHOICES = (
        ('datetime', 'DATETIME'),
        ('int', 'INTEGER'),
        ('str', 'CHARACTER'),
        ('bool', 'BOOLEAN'),
    )

    field_name = models.CharField(max_length=200)
    field_type = models.CharField(max_length=200, choices=DATATYPE_CHOICES,
                                  null=True)
    field_value = models.CharField(max_length=200, null=True)
    overwrite = models.BooleanField(default=False)

    def __str__(self):
        """String for representing the Model object."""
        return f'{self.id}'

    def save(self, *args, **kwargs):
        return super(MetadataFieldOverwrite, self).save(*args, **kwargs)
