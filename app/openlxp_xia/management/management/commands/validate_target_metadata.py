import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from openlxp_xia.management.utils.xia_internal import (
    dict_flatten, is_date, required_recommended_logs)
from openlxp_xia.management.utils.xss_client import (
    get_data_types_for_validation, get_required_fields_for_validation,
    get_target_validation_schema)
from openlxp_xia.models import MetadataLedger, SupplementalLedger

logger = logging.getLogger('dict_config_logger')


def get_target_metadata_for_validation():
    """Retrieving target metadata from MetadataLedger that needs to be
        validated"""
    logger.info(
        "Accessing target metadata from MetadataLedger to be validated")
    target_data_dict = MetadataLedger.objects.values(
        'target_metadata_key_hash',
        'target_metadata').filter(target_metadata_validation_status='',
                                  record_lifecycle_status='Active',
                                  target_metadata_transmission_date=None
                                  ).exclude(
        source_metadata_transformation_date=None)
    return target_data_dict


def update_previous_instance_in_metadata(key_value_hash):
    """Update older instances of record to inactive status"""
    # Setting record_status & deleted_date for updated record
    MetadataLedger.objects.filter(
        source_metadata_key_hash=key_value_hash,
        record_lifecycle_status='Active'). \
        exclude(target_metadata_validation_date=None).update(
        metadata_record_inactivation_date=timezone.now())
    MetadataLedger.objects.filter(
        source_metadata_key_hash=key_value_hash,
        record_lifecycle_status='Active'). \
        exclude(target_metadata_validation_date=None).update(
        record_lifecycle_status='Inactive')

    SupplementalLedger.objects.filter(
        supplemental_metadata_key_hash=key_value_hash,
        record_lifecycle_status='Active'). \
        exclude(supplemental_metadata_validation_date=None).update(
        metadata_record_inactivation_date=timezone.now())
    SupplementalLedger.objects.filter(
        supplemental_metadata_key_hash=key_value_hash,
        record_lifecycle_status='Active'). \
        exclude(supplemental_metadata_validation_date=None).update(
        record_lifecycle_status='Inactive')


def store_target_metadata_validation_status(target_data_dict, key_value_hash,
                                            validation_result,
                                            record_status_result,
                                            target_metadata):
    """Storing validation result in MetadataLedger"""
    if record_status_result == 'Active':
        update_previous_instance_in_metadata(key_value_hash)
        target_data_dict.filter(
            target_metadata_key_hash=key_value_hash).update(
            target_metadata=target_metadata,
            target_metadata_validation_status=validation_result,
            target_metadata_validation_date=timezone.now(),
            record_lifecycle_status=record_status_result)

    else:
        target_data_dict.filter(
            target_metadata_key_hash=key_value_hash).update(
            target_metadata=target_metadata,
            target_metadata_validation_status=validation_result,
            target_metadata_validation_date=timezone.now(),
            record_lifecycle_status=record_status_result,
            metadata_record_inactivation_date=timezone.now())

    SupplementalLedger.objects.filter(
        supplemental_metadata_key_hash=key_value_hash,
        record_lifecycle_status="Active").update(
        supplemental_metadata_validation_date=timezone.now(),
        record_lifecycle_status=record_status_result)


def validate_target_using_key(target_data_dict, required_column_list,
                              recommended_column_list, expected_data_types):
    """Validating target data against required & recommended column names"""

    logger.info('Validating and updating records in MetadataLedger table for '
                'target data')
    len_target_metadata = len(target_data_dict)
    for ind in range(len_target_metadata):
        # Updating default validation for all records
        validation_result = 'Y'
        record_status_result = 'Active'

        # flattened source data created for reference
        flattened_source_data = dict_flatten(target_data_dict[ind]
                                             ['target_metadata'],
                                             required_column_list)
        # validate for required values in data
        for item_name in required_column_list:
            # update validation and record status for invalid data
            # Log out error for missing required values
            # item_name = item[:-len(".use")]
            if item_name in flattened_source_data:
                if not flattened_source_data[item_name]:
                    validation_result = 'N'
                    record_status_result = 'Inactive'
                    required_recommended_logs(ind, "Required", item_name)
            else:
                validation_result = 'N'
                record_status_result = 'Inactive'
                required_recommended_logs(ind, "Required", item_name)

        # validate for recommended values in data
        for item_name in recommended_column_list:
            # Log out warning for missing recommended values
            # item_name = item[:-len(".use")]
            if item_name in flattened_source_data:
                if not flattened_source_data[item_name]:
                    required_recommended_logs(ind, "Recommended", item_name)
            else:
                required_recommended_logs(ind, "Recommended", item_name)
        # Type checking for values in metadata
        for item in flattened_source_data:
            # check if datatype has been assigned to field
            if item in expected_data_types:
                # type checking for datetime datatype fields
                if expected_data_types[item] == "datetime":
                    if not is_date(flattened_source_data[item]):
                        required_recommended_logs(ind, "datatype",
                                                  item)
                # type checking for datatype fields(except datetime)
                elif (not isinstance(flattened_source_data[item],
                                     expected_data_types[item])):
                    required_recommended_logs(ind, "datatype",
                                              item)

        # assigning key hash value for source metadata
        key_value_hash = target_data_dict[ind]['target_metadata_key_hash']
        # Calling function to update validation status
        store_target_metadata_validation_status(target_data_dict,
                                                key_value_hash,
                                                validation_result,
                                                record_status_result,
                                                target_data_dict[ind]
                                                ['target_metadata'])


class Command(BaseCommand):
    """Django command to validate target data"""

    def handle(self, *args, **options):
        """
            target data is validated and stored in metadataLedger
        """
        schema_data_dict = get_target_validation_schema()
        target_data_dict = get_target_metadata_for_validation()
        required_column_list, recommended_column_list = \
            get_required_fields_for_validation(
                schema_data_dict)
        expected_data_types = get_data_types_for_validation(schema_data_dict)
        validate_target_using_key(target_data_dict, required_column_list,
                                  recommended_column_list, expected_data_types)
        logger.info(
            'MetadataLedger updated with target metadata validation status')
