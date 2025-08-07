import html
import bleach
import logging
from confusable_homoglyphs import categories, confusables

logger = logging.getLogger('dict_config_logger')


def bleach_data_to_json(rdata):
    """Recursive function to bleach/clean HTML tags from string
    data and return dictionary data.

    :param rdata: dictionary to clean.
    WARNING rdata will be edited
    :return: dict"""

    keysList = list(rdata.keys())
    for key in keysList:
        if isinstance(rdata[key], str):
            # if string, clean
            rdata[key] = bleach.clean(rdata[key], tags={}, strip=True)
            rdata[key] = html.unescape(rdata[key])
        if isinstance(rdata[key], dict):
            # if dict, enter dict
            rdata[key] = bleach_data_to_json(rdata[key])
    return rdata


def is_safe_string(data):
    """Checks for dangerous homoglyphs."""

    return not (isinstance(data, str) and confusables.is_dangerous(data))


def confusable_homoglyphs_check(d, path=None):
    """
    Recursively iterate to every leaf node
    in a nested dictionary and apply check_func.
    Returns True if all leaf nodes pass the check, False otherwise.
    """
    if path is None:
        path = []
    result = True
    for k, v in d.items():
        if isinstance(v, dict):
            if not confusable_homoglyphs_check(v, path + [k]):
                logger.info(
                    "Homoglyphs does not have the expected preferred alias")
                logger.error(categories.unique_aliases(str(v)))
                result = False
        else:
            if not is_safe_string(v):
                logger.info(
                    "Homoglyphs does not have the expected preferred alias")
                logger.error(categories.unique_aliases(str(v)))
                result = False
    return result
