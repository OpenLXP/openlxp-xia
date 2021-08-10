import logging

import requests

from openlxp_xia.models import XISConfiguration

logger = logging.getLogger('dict_config_logger')


def get_xis_metadata_api_endpoint():
    """Retrieve xis metadata api endpoint from XIS configuration """
    logger.debug("Retrieve XIS metadata ledger api endpoint from "
                 "XIS configuration")
    xis_data = XISConfiguration.objects.first()
    xis_metadata_api_endpoint = xis_data.xis_metadata_api_endpoint
    return xis_metadata_api_endpoint


def get_xis_supplemental_metadata_api_endpoint():
    """Retrieve xis supplemental api endpoint from XIS configuration """
    logger.debug("Retrieve XIS supplemental ledger api endpoint from "
                 "XIS configuration")
    xis_data = XISConfiguration.objects.first()
    xis_supplemental_api_endpoint = xis_data.xis_supplemental_api_endpoint

    return xis_supplemental_api_endpoint


def posting_metadata_ledger_to_xis(renamed_data):
    """This function post data to XIS and returns the XIS response to
            XIA load_target_metadata() """
    headers = {'Content-Type': 'application/json'}

    xis_response = requests.post(url=get_xis_metadata_api_endpoint(),
                                 data=renamed_data, headers=headers)
    return xis_response


def posting_supplemental_metadata_to_xis(renamed_data):
    """This function post data to XIS and returns the XIS response to
            XIA load_target_metadata() """
    headers = {'Content-Type': 'application/json'}

    xis_response = requests.post(
        url=get_xis_supplemental_metadata_api_endpoint(), data=renamed_data,
        headers=headers)
    return xis_response
