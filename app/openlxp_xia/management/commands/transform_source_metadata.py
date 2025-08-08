import hashlib
import logging

import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone

from openlxp_xia.management.utils.xia_internal import (
    get_target_metadata_key_value, is_date, is_scalar, map_nested,
    required_recommended_logs,
    type_cast_overwritten_values)
from openlxp_xia.management.utils.xss_client import (
    get_data_types_for_validation, get_required_fields_for_validation,
    get_scalar_type_for_transformation,
    get_source_validation_schema,
    get_target_metadata_for_transformation,
    get_target_validation_schema)
from openlxp_xia.models import (MetadataFieldOverwrite,
                                MetadataLedger,
                                SupplementalLedger,
                                XIAConfiguration)

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


def get_metadata_fields_to_overwrite(metadata_df):
    """looping through fields to be overwrite or appended"""
    for each in MetadataFieldOverwrite.objects.all():
        column = each.field_name
        overwrite_flag = each.overwrite
        # checking and converting type of overwritten values
        value = type_cast_overwritten_values(each.field_type, each.field_value)

        metadata_df = overwrite_append_metadata(metadata_df, column, value,
                                                overwrite_flag)
    return metadata_df


def overwrite_append_metadata(metadata_df, column, value, overwrite_flag):
    """Overwrite & append metadata fields based on overwrite flag """

    # field should be overwritten and append
    if overwrite_flag:
        metadata_df[column] = value
    # skip field to be overwritten and append
    else:
        if column not in metadata_df.columns:
            metadata_df[column] = value
        else:
            metadata_df.loc[metadata_df[column].isnull(), column] = value
            metadata_df.loc[metadata_df[column] == "", column] = value
    return metadata_df


def overwrite_metadata_field(metadata_df):
    """Overwrite & append metadata fields with admin entered values """
    # get metadata fields to be overwritten and appended and replace values
    metadata_df = get_metadata_fields_to_overwrite(metadata_df)
    # return source metadata as dictionary

    source_data_dict = metadata_df.to_dict(orient='index')
    return source_data_dict[0]


def transform_target_expected_scalar_type(target_data_dict,
                                          expected_scalar_type):
    """Function to transform target data to expected scalar type"""
    for section in target_data_dict:
        if isinstance(target_data_dict[section], dict):
            for key in target_data_dict[section]:
                item = section + '.' + key
                # check if item has a expected datatype from schema
                if item in expected_scalar_type:
                    # check for expected scalar type for field in metadata
                    if (expected_scalar_type[item] is False and
                            not is_scalar(target_data_dict[section][key])):
                        target_data_dict[section][key] = \
                            target_data_dict[section][key][0]
                        logger.warning(
                            f"Expected scalar type for {item} is False, "
                            f"converted to {target_data_dict[section][key]}")
        else:
            item = section
            # check if item has a expected datatype from schema
            if item in expected_scalar_type:
                # check for expected scalar type for field in metadata
                if (expected_scalar_type[item] is False and
                        not is_scalar(target_data_dict[section])):
                    target_data_dict[section] = target_data_dict[section][0]
                    logger.warning(
                        f"Expected scalar type for {item} is False, "
                        f"converted to {target_data_dict[section]}")
    return target_data_dict


def type_checking_target_metadata(ind, target_data_dict, expected_data_types):
    """Function for type checking and explicit type conversion of metadata"""

    # Looping through target data dictionary to check for expected data types
    for section in target_data_dict:
        if isinstance(target_data_dict[section], dict):
            for key in target_data_dict[section]:
                item = str(section) + '.' + key
                # check if item has a expected datatype from schema
                if item in expected_data_types:
                    # check for datetime datatype for field in metadata
                    if expected_data_types[item] == "datetime":
                        if not is_date(target_data_dict[section][key]):
                            # explicitly convert to string if incorrect
                            required_recommended_logs(ind, "datatype",
                                                      item)
                    # check for datatype for field in metadata(except datetime)
                    elif (not isinstance(target_data_dict[section][key],
                                         expected_data_types[item])):
                        # explicitly convert to string if incorrect
                        required_recommended_logs(ind, "datatype",
                                                  item)
        else:
            item = section
            # check if item has a expected datatype from schema
            if item in expected_data_types:
                # check for datetime datatype for field in metadata
                if expected_data_types[item] == "datetime":
                    if not is_date(target_data_dict[section]):
                        # explicitly convert to string if incorrect
                        required_recommended_logs(ind, "datatype",
                                                  item)
                # check for datatype for field in metadata(except datetime)
                elif (not isinstance(target_data_dict[section],
                                     expected_data_types[item])):
                    # explicitly convert to string if incorrect
                    required_recommended_logs(ind, "datatype",
                                              item)
            # explicitly convert to string if datatype not present
    return target_data_dict


def create_target_metadata_dict(ind, target_mapping_dict, source_metadata,
                                required_column_list, expected_data_types,
                                expected_scalar_type):
    """Function to replace and transform source data to target data for
    using target mapping schema"""

    target_schema = pd.json_normalize(target_mapping_dict)

    # Updating null values with empty strings for replacing metadata
    source_metadata = {
        k: '' if not v else v for k, v in
        source_metadata.items()}

    # replacing fields to be overwritten or appended
    metadata_df = pd.json_normalize(source_metadata)
    metadata = overwrite_metadata_field(metadata_df)

    # Replacing metadata schema with mapped values from source metadata

    target_data_dict = map_nested(metadata, target_mapping_dict)

    # type checking and explicit type conversion of metadata
    target_data_dict = type_checking_target_metadata(ind, target_data_dict,
                                                     expected_data_types)
    target_data_dict = \
        transform_target_expected_scalar_type(target_data_dict,
                                              expected_scalar_type)

    # send values to be skipped while creating supplemental data

    supplemental_metadata = \
        create_supplemental_metadata(target_schema.values.tolist(), metadata)

    return target_data_dict, supplemental_metadata


def store_transformed_source_metadata(key_value, key_value_hash,
                                      target_data_dict,
                                      hash_value, supplemental_metadata):
    """Storing target metadata in MetadataLedger"""

    source_extraction_date = MetadataLedger.objects.values_list(
        "source_metadata_extraction_date", flat=True).get(
        source_metadata_key_hash=key_value_hash,
        record_lifecycle_status='Active',
        source_metadata_transformation_date=None
    )

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


def transform_source_using_key(xia, source_data_dict, target_mapping_dict,
                               required_column_list, expected_data_types,
                               expected_scalar_type):
    """Transforming source data using target metadata schema"""
    logger.info(
        "Transforming source data using target renaming and mapping "
        "schemas and storing in json format ")
    logger.info("Identifying supplemental data and storing them ")
    len_source_metadata = len(source_data_dict)
    logger.info(
        "Overwrite & append metadata fields with admin entered values")
    for ind in range(len_source_metadata):
        for table_column_name in source_data_dict[ind]:
            # Looping through target values in dictionary
            target_data_dict, supplemental_metadata = \
                create_target_metadata_dict(ind, target_mapping_dict,
                                            source_data_dict
                                            [ind]
                                            [table_column_name],
                                            required_column_list,
                                            expected_data_types,
                                            expected_scalar_type
                                            )
            # Replacing values in field referring target schema
            # Key creation for target metadata
            key = get_target_metadata_key_value(xia, target_data_dict)

            hash_value = hashlib.sha512(
                str(target_data_dict).encode(
                    'utf-8')).hexdigest()

            if key['key_value']:
                store_transformed_source_metadata(key['key_value'],
                                                  key[
                    'key_value_hash'],
                    target_data_dict,
                    hash_value,
                    supplemental_metadata)
            else:
                logger.error("Cannot store record " +
                             str(ind)+" without Key hash value")


class Command(BaseCommand):
    """Django command to extract data in the Experience index Agent (XIA)"""

    help = 'Transform source metadata'

    def add_arguments(self, parser):
        parser.add_argument('--config_id', type=int, help='ID of the config')

    def handle(self, *args, **options):
        """
            Metadata is transformed in the XIA and stored in Metadata Ledger
        """
        xia = None
        # Check if xia configuration is provided in options
        if 'config' in options:
            xia = options['config'].xia_configuration
            logger.info(xia)
        elif 'config_id' in options:
            # If config_id is provided, fetch the XIAConfiguration object
            try:
                xia = XIAConfiguration.objects.get(id=options['config_id'])
                logger.info(xia)
            except XIAConfiguration.DoesNotExist:
                logger.error(
                    f'XIA Configuration with ID {options["config_id"]} '
                    'does not exist')
                return
        if not xia:
            xia = XIAConfiguration.objects.first()
            if not xia:
                # If xia is not provided, log an error and exit
                logger.error('XIA Configuration is not provided')
                raise SystemExit('XIA Configuration is not provided')
        target_mapping_dict = get_target_metadata_for_transformation(xia)
        source_data_dict = get_source_metadata_for_transformation()
        schema_data_dict = get_source_validation_schema(xia)
        schema_validation = get_target_validation_schema(xia)
        required_column_list, recommended_column_list = \
            get_required_fields_for_validation(schema_data_dict)
        expected_data_types = get_data_types_for_validation(schema_validation)
        expected_scalar_type = get_scalar_type_for_transformation(
            schema_validation)
        transform_source_using_key(xia, source_data_dict, target_mapping_dict,
                                   required_column_list, expected_data_types,
                                   expected_scalar_type)

        logger.info('MetadataLedger updated with transformed data in XIA')
