import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from openlxp_xia.management.utils.xia_internal import (
    dict_flatten, required_recommended_logs)
from openlxp_xia.management.utils.xss_client import (
    get_required_fields_for_validation, get_source_validation_schema)
from openlxp_xia.models import MetadataLedger

logger = logging.getLogger('dict_config_logger')


def get_source_metadata_for_validation():
    """Retrieving source metadata from MetadataLedger that needs to be
        validated"""
    logger.info(
        "Accessing source metadata from MetadataLedger to be validated")
    source_data_dict = \
        MetadataLedger.objects.values('source_metadata_key_hash',
                                      'source_metadata').filter(
            source_metadata_validation_status='',
            record_lifecycle_status='Active').exclude(
            source_metadata_extraction_date=None)

    return source_data_dict


def store_source_metadata_validation_status(source_data_dict,
                                            key_value_hash, validation_result,
                                            record_status_result,
                                            source_metadata):
    """Storing validation result in MetadataLedger"""

    if record_status_result == 'Active':
        source_data_dict.filter(
            source_metadata_key_hash=key_value_hash).update(
            source_metadata=source_metadata,
            source_metadata_validation_status=validation_result,
            source_metadata_validation_date=timezone.now(),
            record_lifecycle_status=record_status_result
        )
    else:
        source_data_dict.filter(
            source_metadata_key_hash=key_value_hash).update(
            source_metadata=source_metadata,
            source_metadata_validation_status=validation_result,
            source_metadata_validation_date=timezone.now(),
            record_lifecycle_status=record_status_result,
            metadata_record_inactivation_date=timezone.now()
        )


def validate_source_using_key(source_data_dict, required_column_list,
                              recommended_column_list):
    """Validating source data against required & recommended column names"""

    logger.info("Validating and updating records in MetadataLedger table for "
                "Source data")
    len_source_metadata = len(source_data_dict)
    for ind in range(len_source_metadata):
        # Updating default validation for all records
        validation_result = 'Y'
        record_status_result = 'Active'

        # flattened source data created for reference
        flattened_source_data = dict_flatten(source_data_dict[ind]
                                             ['source_metadata'],
                                             required_column_list)
        # validate for required values in data
        for item in required_column_list:
            # update validation and record status for invalid data
            # Log out error for missing required values
            if item in flattened_source_data:
                if not flattened_source_data[item]:
                    validation_result = 'N'
                    required_recommended_logs(ind, "Required", item)
            else:
                validation_result = 'N'
                required_recommended_logs(ind, "Required", item)

        # validate for recommended values in data
        for item in recommended_column_list:
            # Log out warning for missing recommended values
            if item in flattened_source_data:
                if not flattened_source_data[item]:
                    required_recommended_logs(ind, "Recommended", item)
            else:
                required_recommended_logs(ind, "Recommended", item)
        # assigning key hash value for source metadata
        key_value_hash = source_data_dict[ind]['source_metadata_key_hash']
        # Calling function to update validation status
        store_source_metadata_validation_status(source_data_dict,
                                                key_value_hash,
                                                validation_result,
                                                record_status_result,
                                                source_data_dict[ind]
                                                ['source_metadata'])


class Command(BaseCommand):
    """Django command to validate source data"""

    def handle(self, *args, **options):
        """
            Source data is validated and stored in metadataLedger
        """
        schema_data_dict = get_source_validation_schema()
        required_column_list, recommended_column_list = \
            get_required_fields_for_validation(schema_data_dict)
        source_data_dict = get_source_metadata_for_validation()
        validate_source_using_key(source_data_dict, required_column_list,
                                  recommended_column_list)

        logger.info(
            'MetadataLedger updated with source metadata validation status')
