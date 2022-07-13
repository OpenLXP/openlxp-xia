import copy
import hashlib
import logging

import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone

from openlxp_xia.management.utils.xia_internal import (
    dict_flatten, get_target_metadata_key_value,
    replace_field_on_target_schema, transform_to_target, traverse_dict,
    traverse_dict_with_key_list, type_cast_overwritten_values,
    type_check_change)
from openlxp_xia.management.utils.xss_client import (
    get_data_types_for_validation, get_required_fields_for_validation,
    get_source_validation_schema, get_target_metadata_for_transformation,
    get_target_validation_schema)
from openlxp_xia.models import (MetadataFieldOverwrite, MetadataLedger,
                                SupplementalLedger)

logger = logging.getLogger('dict_config_logger')


def get_source_metadata_for_transformation():
    """Retrieving Source metadata from MetadataLedger that needs to be
        transformed"""
    logger.info(
        "Retrieving source metadata from MetadataLedger to be transformed")
    source_data_dict = MetadataLedger.objects.values(
        'source_metadata').filter(
        record_lifecycle_status='Active',
        source_metadata_transformation_date=None).exclude(
        source_metadata_validation_date=None)

    return source_data_dict


def create_supplemental_metadata(metadata_columns, supplemental_metadata):
    """Function to identify supplemental metadata store them"""

    for metadata_column_list in metadata_columns:
        for column in metadata_column_list:
            supplemental_metadata.pop(column, None)
    return supplemental_metadata


def overwrite_append_metadata(metadata, column, value, overwrite_flag):
    """Overwrite & append metadata fields based on overwrite flag """

    key_list = column.split(".")
    # loop till last key_value in list
    for key_value in key_list[:-1]:
        metadata = traverse_dict(metadata, key_value)

    column = key_list[-1]
    # field should be overwritten and append
    if overwrite_flag:
        metadata[column] = value
    # skip field to be overwritten and append
    else:
        if column not in metadata:
            metadata[column] = value
        else:
            if metadata[column] is None or metadata[column] == "":
                metadata[column] = value


def overwrite_metadata_field(metadata):
    """Overwrite & append metadata fields with admin entered values """
    # get metadata fields to be overwritten and appended and replace values
    for each in MetadataFieldOverwrite.objects.all():
        column = each.field_name
        overwrite_flag = each.overwrite
        # checking and converting type of overwritten values
        value = type_cast_overwritten_values(each.field_type, each.field_value)

        overwrite_append_metadata(metadata, column, value,
                                  overwrite_flag)
    return metadata


def type_checking_target_metadata(ind, target_data_dict, expected_data_types,
                                  element):
    """Function for type checking and explicit type conversion of metadata"""
    # for element in expected_data_types:
    key_list = element.split(".")
    # check_key_dict = copy.deepcopy(target_data_dict)
    check_key_dict = target_data_dict
    check_key_dict = traverse_dict_with_key_list(check_key_dict, key_list)
    if check_key_dict:
        if key_list[-1] in check_key_dict:
            if isinstance(check_key_dict[key_list[-1]], list):
                for index in range(len(check_key_dict)):
                    type_check_change(ind, element, expected_data_types,
                                      check_key_dict[key_list[-1]],
                                      index)
            else:
                type_check_change(ind, element, expected_data_types,
                                  check_key_dict, key_list[-1])


def create_target_metadata_dict(ind, target_mapping_replace, source_metadata,
                                required_column_list, expected_data_types):
    """Function to replace and transform source data to target data for
    using target mapping schema"""

    # Create dataframe using target metadata schema
    target_schema = pd.DataFrame.from_dict(
        target_mapping_replace,
        orient='index')

    # Flatten source data dictionary for replacing and transformation
    source_metadata = dict_flatten(source_metadata, required_column_list)

    # Updating null values with empty strings for replacing metadata
    source_metadata = {
        k: '' if not v else v for k, v in
        source_metadata.items()}
    target_data_dict = transform_to_target(source_metadata,
                                           target_mapping_replace)

    # replacing fields to be overwritten or appended
    overwrite_metadata_field(target_data_dict)

    # type checking and explicit type conversion of metadata
    for element in expected_data_types:
        data = copy.copy(target_data_dict)
        type_checking_target_metadata(ind, data,
                                      expected_data_types, element)

    # send values to be skipped while creating supplemental data
    supplemental_metadata = \
        create_supplemental_metadata(target_schema.values.tolist(),
                                     source_metadata)

    return target_data_dict, supplemental_metadata


def store_transformed_source_metadata(key_value, key_value_hash,
                                      target_data_dict,
                                      hash_value, supplemental_metadata):
    """Storing target metadata in MetadataLedger"""

    source_extraction_date = MetadataLedger.objects.values_list(
        "source_metadata_extraction_date", flat=True).filter(
        source_metadata_key_hash=key_value_hash,
        record_lifecycle_status='Active'
    ).first()

    data_for_transformation = MetadataLedger.objects.filter(
        source_metadata_key_hash=key_value_hash,
        record_lifecycle_status='Active',
        source_metadata_transformation_date=None
    )

    if data_for_transformation.values("target_metadata_hash") != hash_value:
        data_for_transformation.update(target_metadata_validation_status='')

    data_for_transformation.update(
        source_metadata_transformation_date=timezone.now(),
        target_metadata_key=key_value,
        target_metadata_key_hash=key_value_hash,
        target_metadata=target_data_dict,
        target_metadata_hash=hash_value)

    supplemental_hash_value = hashlib.sha512(
        str(supplemental_metadata).encode(
            'utf-8')).hexdigest()

    # check if metadata has corresponding supplemental values and store
    if supplemental_metadata:
        SupplementalLedger.objects.get_or_create(
            supplemental_metadata_hash=supplemental_hash_value,
            supplemental_metadata_key=key_value,
            supplemental_metadata_key_hash=key_value_hash,
            supplemental_metadata=supplemental_metadata,
            record_lifecycle_status='Active')

        SupplementalLedger.objects.filter(
            supplemental_metadata_hash=supplemental_hash_value,
            supplemental_metadata_key=key_value,
            supplemental_metadata_key_hash=key_value_hash,
            record_lifecycle_status='Active').update(
            supplemental_metadata_extraction_date=source_extraction_date,
            supplemental_metadata_transformation_date=timezone.now())


def transform_source_using_key(source_data_dict, target_mapping,
                               required_column_list, expected_data_types):
    """Transforming source data using target metadata schema"""
    logger.info(
        "Transforming source data using target renaming and mapping "
        "schemas and storing in json format ")
    logger.info("Identifying supplemental data and storing them ")
    len_source_metadata = len(source_data_dict)
    logger.info(
        "Overwrite & append metadata fields with admin entered values")
    for ind in range(len_source_metadata):
        target_mapping_metadata = copy.deepcopy(target_mapping)
        target_metadata, supplemental_metadata = \
            create_target_metadata_dict(ind, target_mapping_metadata,
                                        source_data_dict
                                        [ind]
                                        ['source_metadata'],
                                        required_column_list,
                                        expected_data_types
                                        )
        # Replacing values in field referring target schema
        replace_field_on_target_schema(ind,
                                       target_metadata)
        # Key creation for target metadata
        key = get_target_metadata_key_value(target_metadata)

        hash_value = hashlib.sha512(
            str(target_metadata).encode(
                'utf-8')).hexdigest()
        store_transformed_source_metadata(key['key_value'],
                                          key[
                                              'key_value_hash'],
                                          target_metadata,
                                          hash_value,
                                          supplemental_metadata)


class Command(BaseCommand):
    """Django command to extract data in the Experience index Agent (XIA)"""

    def handle(self, *args, **options):
        """
            Metadata is transformed in the XIA and stored in Metadata Ledger
        """
        target_mapping_dict = get_target_metadata_for_transformation()
        source_data_dict = get_source_metadata_for_transformation()
        schema_data_dict = get_source_validation_schema()
        schema_validation = get_target_validation_schema()
        required_column_list, recommended_column_list = \
            get_required_fields_for_validation(schema_data_dict)
        expected_data_types = get_data_types_for_validation(schema_validation)
        transform_source_using_key(source_data_dict, target_mapping_dict,
                                   required_column_list, expected_data_types)

        logger.info('MetadataLedger updated with transformed data in XIA')
