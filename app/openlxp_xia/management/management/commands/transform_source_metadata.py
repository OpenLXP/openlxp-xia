import hashlib
import logging

import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone

from openlxp_xia.management.utils.xia_internal import (
    dict_flatten, get_target_metadata_key_value, is_date,
    replace_field_on_target_schema, required_recommended_logs,
    type_cast_overwritten_values)
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


def type_checking_target_metadata(ind, target_data_dict, expected_data_types):
    """Function for type checking and explicit type conversion of metadata"""
    for index in target_data_dict:
        for section in target_data_dict[index]:
            for key in target_data_dict[index][section]:
                item = section + '.' + key
                # check if item has a expected datatype from schema
                if item in expected_data_types:
                    # check for datetime datatype for field in metadata
                    if expected_data_types[item] == "datetime":
                        if not is_date(target_data_dict[index][section][key]):
                            # explicitly convert to string if incorrect
                            target_data_dict[index][section][key] = str(
                                target_data_dict[index][section][key])
                            required_recommended_logs(ind, "datatype",
                                                      item)
                    # check for datatype for field in metadata(except datetime)
                    elif (not isinstance(target_data_dict[index][section][key],
                                         expected_data_types[item])):
                        # explicitly convert to string if incorrect
                        target_data_dict[index][section][key] = str(
                            target_data_dict[index][section][key])
                        required_recommended_logs(ind, "datatype",
                                                  item)
                # explicitly convert to string if datatype not present
                else:
                    target_data_dict[index][section][key] = str(
                        target_data_dict[index][section][key])
    return target_data_dict


def create_target_metadata_dict(ind, target_mapping_dict, source_metadata,
                                required_column_list, expected_data_types):
    """Function to replace and transform source data to target data for
    using target mapping schema"""

    # Create dataframe using target metadata schema
    target_schema = pd.DataFrame.from_dict(
        target_mapping_dict,
        orient='index')

    # Flatten source data dictionary for replacing and transformation
    source_metadata = dict_flatten(source_metadata, required_column_list)

    # Updating null values with empty strings for replacing metadata
    source_metadata = {
        k: '' if not v else v for k, v in
        source_metadata.items()}

    # replacing fields to be overwritten or appended
    metadata_df = pd.DataFrame(source_metadata, index=[0])
    metadata = overwrite_metadata_field(metadata_df)

    # Replacing metadata schema with mapped values from source metadata

    target_schema_replaced = target_schema.replace(metadata)

    # Dropping index value and creating json object
    target_data = target_schema_replaced.apply(lambda x: [x.dropna()],
                                               axis=1).to_json()
    # Creating dataframe from json object
    target_data_df = pd.read_json(target_data)

    # transforming target dataframe to dictionary object for replacing
    # values in target with new value
    target_data_dict = target_data_df.to_dict(orient='index')

    # type checking and explicit type conversion of metadata
    target_data_dict = type_checking_target_metadata(ind, target_data_dict,
                                                     expected_data_types)

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


def transform_source_using_key(source_data_dict, target_mapping_dict,
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
        for table_column_name in source_data_dict[ind]:
            target_data_dict, supplemental_metadata = \
                create_target_metadata_dict(ind, target_mapping_dict,
                                            source_data_dict
                                            [ind]
                                            [table_column_name],
                                            required_column_list,
                                            expected_data_types
                                            )
            # Looping through target values in dictionary
            for ind1 in target_data_dict:
                # Replacing values in field referring target schema
                replace_field_on_target_schema(ind1,
                                               target_data_dict)
                # Key creation for target metadata
                key = get_target_metadata_key_value(target_data_dict[ind1])

                hash_value = hashlib.sha512(
                    str(target_data_dict[ind1]).encode(
                        'utf-8')).hexdigest()
                store_transformed_source_metadata(key['key_value'],
                                                  key[
                                                      'key_value_hash'],
                                                  target_data_dict[
                                                      ind1],
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
