import logging

import requests
from django.core.cache import cache

from openlxp_xia.management.utils.xia_internal import dict_flatten
from openlxp_xia.models import XIAConfiguration

logger = logging.getLogger('dict_config_logger')


def xss_get(xia_config=None):
    """Function to get xss configuration value"""
    conf = xia_config if xia_config else XIAConfiguration.objects.first()
    if not conf or not conf.xss_api:
        logger.error("XSS API configuration is not set.")
        raise ValueError("XSS API configuration is not set.")
    return conf.xss_api


def read_json_data(xia_config, source_schema_ref, target_schema_ref=None):
    """get schema from xss and ingest as dictionary values"""
    xss_host = xss_get(xia_config)
    request_path = xss_host

    if request_path[-1] != '/':
        request_path += '/'
    if not request_path.endswith('api/'):
        request_path += 'api/'
    if (target_schema_ref is not None):
        # check cache for schema
        cached_schema = cache.get(
            source_schema_ref + 'map' + target_schema_ref)
        if cached_schema:
            return cached_schema
        if (target_schema_ref.startswith('xss:')):
            request_path += 'mappings/?targetIRI=' + target_schema_ref
        else:
            request_path += 'mappings/?targetName=' + target_schema_ref
        if (source_schema_ref.startswith('xss:')):
            request_path += '&sourceIRI=' + source_schema_ref
        else:
            request_path += '&sourceName=' + source_schema_ref
        schema = requests.get(request_path, verify=False)
        json_content = schema.json()['schema_mapping']
        cache.add(source_schema_ref + 'map' +
                  target_schema_ref, json_content, timeout=10)
    else:
        cached_schema = cache.get(source_schema_ref)
        if cached_schema:
            return cached_schema
        if (source_schema_ref.startswith('xss:')):
            request_path += 'schemas/?iri=' + source_schema_ref
        else:
            request_path += 'schemas/?name=' + source_schema_ref
        schema = requests.get(request_path, verify=False)
        json_content = schema.json()['schema']
        cache.add(source_schema_ref, json_content, timeout=10)
    return json_content


def get_source_validation_schema(xia_config=None):
    """Retrieve source validation schema from XIA configuration """
    logger.info("Configuration of schemas and files for source")
    if not xia_config:
        xia_data = XIAConfiguration.objects.first()
    else:
        xia_data = xia_config
    if xia_data.source_metadata_schema is None:
        logger.warning("Source validation field name is empty!")
    logger.info("Reading schema for validation")
    source_validation_schema = xia_data.source_metadata_schema
    if not source_validation_schema:
        logger.warning("Source validation field name is empty!")
    logger.info("Reading schema for validation")
    # Read source validation schema as dictionary
    schema_data_dict = read_json_data(xia_data, source_validation_schema)
    return schema_data_dict


def get_target_validation_schema(xia_config=None):
    """Retrieve target validation schema from XIA configuration """
    logger.info("Configuration of schemas and files for target")
    if not xia_config:
        xia_data = XIAConfiguration.objects.first()
    else:
        xia_data = xia_config
    if xia_data.target_metadata_schema is None:
        logger.warning("Target validation field name is empty!")
    logger.info("Reading schema for validation")
    target_validation_schema = xia_data.target_metadata_schema
    if not target_validation_schema:
        logger.warning("Target validation field name is empty!")
    logger.info("Reading schema for validation")
    # Read source validation schema as dictionary
    schema_data_dict = read_json_data(xia_data, target_validation_schema)
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


def get_scalar_type_for_transformation(schema_data_dict):
    """Creating list of fields with the expected scalar type objects"""

    # Call function to flatten schema used for transformation
    flattened_schema_dict = dict_flatten(schema_data_dict, [])
    expected_scalar_types = dict()

    #  updating dictionary with expected
    #  scalar type values for fields in metadata
    for column, value in flattened_schema_dict.items():
        if column.endswith(".multiple_expected"):
            key = column[:-len(".multiple_expected")]
            expected_scalar_types.update({key: value})

    # Returning required and recommended list for validation
    return expected_scalar_types


def get_data_types_for_validation(schema_data_dict):
    """Creating list of fields with the expected datatype objects"""

    # Call function to flatten schema used for validation
    flattened_schema_dict = dict_flatten(schema_data_dict, [])

    # mapping from string to datatype objects
    datatype_to_object = {
        "int": int,
        "str": str,
        "URI": str,
        "bool": bool,
        "list": list,
        "dict": dict
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


def get_target_metadata_for_transformation(xia_config=None):
    """Retrieve target metadata schema from XIA configuration """
    logger.info("Configuration of schemas and files for transformation")
    if not xia_config:
        xia_data = XIAConfiguration.objects.first()
    else:
        xia_data = xia_config
    # Read target and source transformation schema as dictionary
    target_metadata_schema = xia_data.target_metadata_schema
    source_metadata_schema = xia_data.source_metadata_schema
    if not target_metadata_schema or not source_metadata_schema:
        logger.warning("Metadata schema field name is empty!")
    logger.info("Reading schema for transformation")
    # Read source transformation schema as dictionary
    target_mapping_dict = read_json_data(xia_data,
                                         source_metadata_schema,
                                         target_metadata_schema)
    return target_mapping_dict
