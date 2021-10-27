import json
import logging
import os

import boto3

from openlxp_xia.management.utils.xia_internal import dict_flatten
from openlxp_xia.models import XIAConfiguration

logger = logging.getLogger('dict_config_logger')


def get_aws_bucket_name():
    """function returns the source bucket name"""
    bucket = os.environ.get('BUCKET_NAME')
    return bucket


def read_json_data(file_name):
    """Setting file path for json files and ingesting as dictionary values """
    s3 = boto3.resource('s3')
    bucket_name = get_aws_bucket_name()
    # Read json file and store as a dictionary for processing
    json_path = s3.Object(bucket_name, file_name)
    json_content = json_path.get()['Body'].read().decode('utf-8')
    data_dict = json.loads(json_content)
    return data_dict


def get_source_validation_schema():
    """Retrieve source validation schema from XIA configuration """
    logger.info("Configuration of schemas and files for source")
    xia_data = XIAConfiguration.objects.first()
    source_validation_schema = xia_data.source_metadata_schema
    if not source_validation_schema:
        logger.warning("Source validation field name is empty!")
    logger.info("Reading schema for validation")
    # Read source validation schema as dictionary
    schema_data_dict = read_json_data(source_validation_schema)
    return schema_data_dict


def get_target_validation_schema():
    """Retrieve target validation schema from XIA configuration """
    logger.info("Configuration of schemas and files for target")
    xia_data = XIAConfiguration.objects.first()
    target_validation_schema = xia_data.target_metadata_schema
    if not target_validation_schema:
        logger.warning("Target validation field name is empty!")
    logger.info("Reading schema for validation")
    # Read source validation schema as dictionary
    schema_data_dict = read_json_data(target_validation_schema)
    return schema_data_dict


def get_required_fields_for_validation(schema_data_dict):
    """Creating list of fields which are Required & Recommended"""

    # Call function to flatten schema used for validation
    flattened_schema_dict = dict_flatten(schema_data_dict, [])

    # Declare list for required and recommended column names
    required_column_list = list()
    recommended_column_list = list()

    #  Adding values to required and recommended list based on schema
    for column, value in flattened_schema_dict.items():
        if value == "Required":
            if column.endswith(".use"):
                column = column[:-len(".use")]
            required_column_list.append(column)
        elif value == "Recommended":
            if column.endswith(".use"):
                column = column[:-len(".use")]
            recommended_column_list.append(column)

    # Returning required and recommended list for validation
    return required_column_list, recommended_column_list


def get_data_types_for_validation(schema_data_dict):
    """Creating list of fields with the expected datatype objects"""

    # Call function to flatten schema used for validation
    flattened_schema_dict = dict_flatten(schema_data_dict, [])

    # mapping from string to datatype objects
    datatype_to_object = {
        "int": int,
        "str": str,
        "bool": bool
    }
    expected_data_types = dict()

    #  updating dictionary with expected datatype values for fields in metadata
    for column, value in flattened_schema_dict.items():
        if column.endswith(".data_type"):
            key = column[:-len(".data_type")]
            if value in datatype_to_object:
                value = datatype_to_object[value]
            expected_data_types.update({key: value})

    # Returning required and recommended list for validation
    return expected_data_types


def get_target_metadata_for_transformation():
    """Retrieve target metadata schema from XIA configuration """
    logger.info("Configuration of schemas and files for transformation")
    xia_data = XIAConfiguration.objects.first()
    target_metadata_schema = xia_data.source_target_mapping
    if not target_metadata_schema:
        logger.warning("Target metadata schema field name is empty!")
    logger.info("Reading schema for transformation")
    # Read source transformation schema as dictionary
    target_mapping_dict = read_json_data(target_metadata_schema)
    return target_mapping_dict
