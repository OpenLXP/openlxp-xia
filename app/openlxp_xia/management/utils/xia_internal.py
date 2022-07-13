import copy
import datetime
import hashlib
import logging
from distutils.util import strtobool

from dateutil.parser import parse

from openlxp_xia.models import XIAConfiguration

logger = logging.getLogger('dict_config_logger')


def get_publisher_detail():
    """Retrieve publisher from XIA configuration """
    logger.debug("Retrieve publisher from XIA configuration")
    xia_data = XIAConfiguration.objects.first()
    publisher = xia_data.publisher
    return publisher


def get_key_dict(key_value, key_value_hash):
    """Creating key dictionary with all corresponding key values"""
    key = {'key_value': key_value, 'key_value_hash': key_value_hash}
    return key


def replace_field_on_target_schema(ind1,
                                   target_data_dict):
    """Replacing values in field referring target schema EducationalContext to
    course.MANDATORYTRAINING"""

    field_list = ["Course.EducationalContext"]

    for field in field_list:
        key_list = field.split(".")
        check_key_dict = target_data_dict
        check_key_dict = traverse_dict_with_key_list(check_key_dict, key_list)
        if check_key_dict:
            if key_list[-1] in check_key_dict:
                if check_key_dict[key_list[-1]] == 'y' or \
                        check_key_dict[key_list[-1]] == 'Y':
                    check_key_dict[key_list[-1]] = 'Mandatory'
                else:
                    if check_key_dict[key_list[-1]] or \
                            check_key_dict[key_list[-1]] == 'N':
                        check_key_dict[key_list[-1]] = 'Non - ' \
                                                       'Mandatory'


def get_target_metadata_key_value(data_dict):
    """Function to create key value for target metadata """

    field_list = ["Course.CourseCode", "Course.CourseProviderName"]

    field_values = []

    for key_field in field_list:
        key_list = key_field.split(".")
        key_dict = copy.deepcopy(data_dict)
        key_dict = traverse_dict_with_key_list(key_dict, key_list)
        if key_dict:
            if key_list[-1] in key_dict:
                field_values.append(key_dict[key_list[-1]])
            else:
                logger.error('Field name ' + key_list[-1] + ' is missing for '
                                                            'key creation')
    # Key value creation for source metadata
    key_value = '_'.join(field_values)

    # Key value hash creation for source metadata
    key_value_hash = hashlib.sha512(key_value.encode('utf-8')).hexdigest()

    # Key dictionary creation for source metadata
    key = get_key_dict(key_value, key_value_hash)

    return key


def required_recommended_logs(id_num, category, field):
    """logs the missing required and recommended """

    # Logs the missing required columns
    if category == 'Required':
        logger.error(
            "Record " + str(
                id_num) + " does not have all " + category +
            " fields."
            + field + " field is empty")

    # Logs the missing recommended columns
    if category == 'Recommended':
        logger.warning(
            "Record " + str(
                id_num) + " does not have all " + category +
            " fields."
            + field + " field is empty")

    # Logs the inaccurate datatype columns
    if category == 'datatype':
        logger.warning(
            "Record " + str(
                id_num) + " does not have the expected " + category +
            " for the field " + field)


def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    if isinstance(string, str):
        try:
            parse(string, fuzzy=fuzzy)
            return True

        except ValueError:
            return False
    else:
        return False


def traverse_dict(metadata, key_val):
    """Function to traverse through dict"""
    if key_val not in metadata:
        metadata[key_val] = {}
    return metadata[key_val]


def traverse_dict_with_key_list(check_key_dict, key_list):
    """Function to traverse through dict with a key list"""
    for key in key_list[:-1]:
        if key in check_key_dict:
            check_key_dict = check_key_dict[key]
        else:
            check_key_dict = None
            logger.error("Path to traverse dictionary is "
                         "incorrect/ does not exist")
            return check_key_dict
    return check_key_dict


def dict_flatten(data_dict, required_column_list):
    """Function to flatten/normalize  data dictionary"""

    # assign flattened json object to variable
    flatten_dict = {}

    # Check every key elements value in data
    for element in data_dict:
        # If Json Field value is a Nested Json
        if isinstance(data_dict[element], dict):
            flatten_dict_object(data_dict[element],
                                element, flatten_dict, required_column_list)
        # If Json Field value is a list
        elif isinstance(data_dict[element], list):
            flatten_list_object(data_dict[element],
                                element, flatten_dict, required_column_list)
        # If Json Field value is a string
        else:
            update_flattened_object(data_dict[element],
                                    element, flatten_dict)

    # Return the flattened json object
    return flatten_dict


def flatten_list_object(list_obj, prefix, flatten_dict, required_column_list):
    """function to flatten list object"""
    required_prefix_list = []
    for i in range(len(list_obj)):
        #  storing initial flatten_dict for resetting values
        if not i:
            flatten_dict_temp = flatten_dict
        # resetting flatten_dict to initial value
        else:
            flatten_dict = flatten_dict_temp

        if isinstance(list_obj[i], list):
            flatten_list_object(list_obj[i], prefix, flatten_dict,
                                required_column_list)

        elif isinstance(list_obj[i], dict):
            flatten_dict_object(list_obj[i], prefix, flatten_dict,
                                required_column_list)

        else:
            update_flattened_object(list_obj, prefix, flatten_dict)

        # looping through required column names
        for required_prefix in required_column_list:
            # finding matching value along with index
            try:
                required_prefix.index(prefix)
            except ValueError:
                continue
            else:
                if required_prefix.index(prefix) == 0:
                    required_prefix_list.append(required_prefix)
        #  setting up flag for checking validation
        passed = True

        # looping through items in required columns with matching prefix
        for item_to_check in required_prefix_list:
            #  flag if value not found
            if item_to_check in flatten_dict:
                if not flatten_dict[item_to_check]:
                    passed = False
            else:
                passed = False

        # if all required values are skip other object in list
        if passed:
            break


def flatten_dict_object(dict_obj, prefix, flatten_dict, required_column_list):
    """function to flatten dictionary object"""
    for element in dict_obj:
        if isinstance(dict_obj[element], dict):
            flatten_dict_object(dict_obj[element], prefix + "." +
                                element, flatten_dict, required_column_list)

        elif isinstance(dict_obj[element], list):
            flatten_list_object(dict_obj[element], prefix + "." +
                                element, flatten_dict, required_column_list)

        else:
            update_flattened_object(dict_obj[element], prefix + "." +
                                    element, flatten_dict)


def update_flattened_object(obj, prefix, flatten_dict):
    """function to update flattened object to dict variable"""

    flatten_dict.update({prefix: obj})


def convert_date_to_isoformat(date):
    """function to convert date to ISO format"""
    if isinstance(date, datetime.datetime):
        date = date.isoformat()
    return date


def type_cast_overwritten_values(field_type, field_value):
    """function to check type of overwritten value and convert it into
    required format"""
    value = field_value
    if field_value:
        if field_type == "int":
            try:
                value = int(field_value)
            except ValueError:
                logger.error("Field Value " + field_value +
                             " and Field Data type " + field_type +
                             " is not valid")
            except TypeError:
                logger.error("Field Value " + field_value +
                             " and Field Data type " + field_type +
                             " do not match")

        if field_type == "bool":
            try:
                value = strtobool(field_value)
            except ValueError:
                logger.error("Field Value " + field_value +
                             " and Field Data type " + field_type +
                             " is not valid")
            except TypeError:
                logger.error("Field Value " + field_value +
                             " and Field Data type " + field_type +
                             " do not match")
        if field_type == "datetime":
            try:
                is_date(field_value)
            except ValueError:
                logger.error("Field Value " + field_value +
                             " and Field Data type " + field_type +
                             " is not valid")
            except TypeError:
                logger.error("Field Value " + field_value +
                             " and Field Data type " + field_type +
                             " do not match")
    else:
        return None

    return value


def assign_target_value_str_list(source_metadata, target_mapping, element):
    """Function to replace source key with source value in target metadata"""
    if target_mapping[element] in source_metadata:
        target_mapping[element] = \
            source_metadata[target_mapping[element]]
    else:
        target_mapping[element] = None


def transform_to_target(source_metadata, target_mapping):
    """Function to transform source to target"""
    for element in target_mapping:
        if isinstance(target_mapping[element], dict):
            transform_to_target(source_metadata, target_mapping[element])
        elif isinstance(target_mapping[element], str) or \
                isinstance(target_mapping[element], list):
            assign_target_value_str_list(
                source_metadata, target_mapping, element)

    return target_mapping


def type_check_change(ind, item, expected_data_types, target_data_dict, index):
    """Function for type checking explicitly converting datatype"""
    if item in expected_data_types:
        # data path assignment if type check is for a list or an element
        if isinstance(index, int):
            data_path = item + "." + str(index)
        else:
            data_path = item
        # check for datetime datatype for field in metadata
        if expected_data_types[item] == "datetime":
            if not is_date(target_data_dict[index]):
                # explicitly convert to string if incorrect
                target_data_dict[index] = str(
                    target_data_dict[index])
                required_recommended_logs(ind, "datatype",
                                          data_path)
        # check for datatype for field in metadata(except datetime)
        elif (not isinstance(target_data_dict[index],
                             expected_data_types[item])):
            # explicitly convert to string if incorrect
            target_data_dict[index] = str(
                target_data_dict[index])
            required_recommended_logs(ind, "datatype",
                                      data_path)


def traverse_metadata(metadata):
    # Check every key elements value in data
    for element in metadata:
        # If Json Field value is a Nested Json
        if isinstance(metadata[element], dict):
            for sub_element in metadata[element]:
                if isinstance(metadata[element][sub_element], dict):
                    traverse_metadata(metadata[element])
                # If Json Field value is a string
                elif isinstance(metadata[element][sub_element], str) or \
                        isinstance(metadata[element][sub_element], list):
                    return metadata[element]
                break
