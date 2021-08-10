import datetime
import hashlib
import logging
from distutils.util import strtobool

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

    target_name = {
        "Course": [
            "EducationalContext",
        ]
    }
    for target_section_name in target_name:
        for target_field_name in target_name[target_section_name]:
            if target_data_dict[ind1][target_section_name]. \
                    get(target_field_name):

                if target_data_dict[ind1][target_section_name][
                    target_field_name] == 'y' or \
                        target_data_dict[ind1][
                            target_section_name][
                            target_field_name] == 'Y':
                    target_data_dict[ind1][
                        target_section_name][
                        target_field_name] = 'Mandatory'
                else:
                    if target_data_dict[ind1][
                        target_section_name][
                        target_field_name] == 'n' or \
                            target_data_dict[ind1][
                                target_section_name][
                                target_field_name] == 'N':
                        target_data_dict[ind1][
                            target_section_name][
                            target_field_name] = 'Non - ' \
                                                 'Mandatory'


def get_target_metadata_key_value(data_dict):
    """Function to create key value for target metadata """
    field = {
        "Course": [
            "CourseCode",
            "CourseProviderName"
        ]
    }

    field_values = []

    for item_section in field:
        for item_name in field[item_section]:
            if not data_dict[item_section].get(item_name):
                logger.info('Field name ' + item_name + ' is missing for '
                                                        'key creation')
            field_values.append(data_dict[item_section].get(item_name))

    # Key value creation for source metadata
    key_value = '_'.join(field_values)

    # Key value hash creation for source metadata
    key_value_hash = hashlib.md5(key_value.encode('utf-8')).hexdigest()

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
            update_flattened_object(list_obj[i], prefix, flatten_dict)

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
            if not flatten_dict[item_to_check]:
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


def update_flattened_object(str_obj, prefix, flatten_dict):
    """function to update flattened object to dict variable"""

    flatten_dict.update({prefix: str_obj})


def convert_date_to_isoformat(date):
    """function to convert date to ISO format"""
    if isinstance(date, datetime.datetime):
        date = date.isoformat()
    return date


def type_cast_overwritten_values(field_type, field_value):
    """function to check type of overwritten value and convert it into
    required format"""
    value = field_value
    if field_type == "int":
        try:
            value = int(field_value)
        except ValueError:
            logger.error("Field Value " + field_value +
                         " and Field Data type " + field_type +
                         " do not match")
    if field_type == "bool":
        try:
            value = strtobool(field_value)
        except ValueError:
            logger.error("Field Value " + field_value +
                         " and Field Data type " + field_type +
                         " do not match")
    return value
