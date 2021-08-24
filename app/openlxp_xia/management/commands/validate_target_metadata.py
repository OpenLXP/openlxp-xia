import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from openlxp_xia.management.utils.xia_internal import (
    dict_flatten, required_recommended_logs)
from openlxp_xia.management.utils.xss_client import (
    get_required_fields_for_validation, get_target_validation_schema)
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
        supplemental_metadata_key_hash=key_value_hash).update(
        supplemental_metadata_validation_date=timezone.now())


def validate_target_using_key(target_data_dict, required_column_list,
                              recommended_column_list):
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
        for item in required_column_list:
            target_metadata = target_data_dict[ind]['target_metadata']
            split_items = item.split('.')
            len_split_items = len(split_items)
            # update validation and record status for invalid data
            # Log out error for missing required values
            if item in flattened_source_data:
                if not flattened_source_data[item]:
                    # Added default value for missing columns
                    for index1 in range(len_split_items - 1):
                        if split_items[index1] in target_metadata:
                            target_metadata = target_metadata[
                                split_items[index1]]
                        else:
                            target_metadata[split_items[index1]] = {}
                            target_metadata = target_metadata[
                                split_items[index1]]
                    target_metadata[
                        split_items[len_split_items - 1]] = "Unavailable"
                    # commented out code for validation
                    validation_result = 'N'
                    # record_status_result = 'Inactive'
                    required_recommended_logs(ind, "Required", item)
            else:
                # Added default value for missing columns
                for index1 in range(len_split_items-1):
                    if split_items[index1] in target_metadata:
                        target_metadata = target_metadata[split_items[index1]]
                    else:
                        target_metadata[split_items[index1]] = {}
                        target_metadata = target_metadata[split_items[index1]]
                target_metadata[
                    split_items[len_split_items - 1]] = "Unavailable"
                # Added default value for missing columns
                validation_result = 'N'
                # record_status_result = 'Inactive'
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
        validate_target_using_key(target_data_dict, required_column_list,
                                  recommended_column_list)
        logger.info(
            'MetadataLedger updated with target metadata validation status')
