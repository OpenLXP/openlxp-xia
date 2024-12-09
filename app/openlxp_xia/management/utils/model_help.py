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


def confusable_homoglyphs_check(data):
    """Checks for dangerous homoglyphs."""

    data_is_safe = True
    for key in data:

        # if string, Check homoglyph
        if isinstance(data[key], str) and bool(confusables.
                                               is_dangerous(data[key])):
            data_is_safe = False
            logger.info("Homoglyphs does not have the expected prefered alias")
            logger.error(categories.unique_aliases(data[key]))
        # if dict, enter dict
        if isinstance(data[key], dict):
            ret_val = confusable_homoglyphs_check(data[key])
            if not ret_val:
                data_is_safe = False
    return data_is_safe
