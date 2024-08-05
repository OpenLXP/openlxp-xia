import logging

import requests

from openlxp_xia.management.utils.xia_internal import dict_flatten
from openlxp_xia.models import XIAConfiguration

logger = logging.getLogger('dict_config_logger')


def xss_get():
    """Function to get xss configuration value"""
    conf = XIAConfiguration.objects.first()
    return conf.xss_api


def read_json_data(source_schema_ref, target_schema_ref=None):
    """get schema from xss and ingest as dictionary values"""
    xss_host = xss_get()
    request_path = xss_host
    if(target_schema_ref is not None):
        if(target_schema_ref.startswith('xss:')):
            request_path += 'mappings/?targetIRI=' + target_schema_ref
        else:
            request_path += 'mappings/?targetName=' + target_schema_ref
        if(source_schema_ref.startswith('xss:')):
            request_path += '&sourceIRI=' + source_schema_ref
        else:
            request_path += '&sourceName=' + source_schema_ref
        schema = requests.get(request_path, verify=True)
        json_content = schema.json()['schema_mapping']
    else:
        if(source_schema_ref.startswith('xss:')):
            request_path += 'schemas/?iri=' + source_schema_ref
        else:
            request_path += 'schemas/?name=' + source_schema_ref
        schema = requests.get(request_path, verify=True)
        json_content = schema.json()['schema']
    return json_content


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
    target_metadata_schema = xia_data.target_metadata_schema
    source_metadata_schema = xia_data.source_metadata_schema
    if not target_metadata_schema or not source_metadata_schema:
        logger.warning("Metadata schema field name is empty!")
    logger.info("Reading schema for transformation")
    # Read source transformation schema as dictionary
    target_mapping_dict = read_json_data(
        source_metadata_schema, target_metadata_schema)
    return target_mapping_dict
