import logging

import requests
from requests.auth import AuthBase

from openlxp_xia.models import XISConfiguration

logger = logging.getLogger('dict_config_logger')


def get_xis_metadata_api_endpoint(xis=None):
    """Retrieve xis metadata api endpoint from XIS configuration """
    logger.debug("Retrieve XIS metadata ledger api endpoint from "
                 "XIS configuration")
    if not xis:
        xis_data = XISConfiguration.objects.first()
    else:
        xis_data = xis
    if not xis_data:  # pragma: no cover
        logger.error("XIS configuration is not set.")
        raise ValueError("XIS configuration is not set.")
    xis_metadata_api_endpoint = xis_data.xis_metadata_api_endpoint
    if xis_metadata_api_endpoint[-1] != '/':
        xis_metadata_api_endpoint += '/'
    if not xis_metadata_api_endpoint.endswith('api/metadata/'):
        xis_metadata_api_endpoint += 'api/metadata/'

    return xis_metadata_api_endpoint


def get_xis_supplemental_metadata_api_endpoint(xis=None):
    """Retrieve xis supplemental api endpoint from XIS configuration """
    logger.debug("Retrieve XIS supplemental ledger api endpoint from "
                 "XIS configuration")
    if not xis:
        xis_data = XISConfiguration.objects.first()
    else:
        xis_data = xis
    if not xis_data:  # pragma: no cover
        logger.error("XIS configuration is not set.")
        raise ValueError("XIS configuration is not set.")
    xis_supplemental_api_endpoint = xis_data.xis_supplemental_api_endpoint
    if xis_supplemental_api_endpoint[-1] != '/':
        xis_supplemental_api_endpoint += '/'
    if not xis_supplemental_api_endpoint.endswith('api/supplemental-data/'):
        xis_supplemental_api_endpoint += 'api/supplemental-data/'

    return xis_supplemental_api_endpoint


def posting_metadata_ledger_to_xis(xis, renamed_data):
    """This function post data to XIS and returns the XIS response to
            XIA load_target_metadata() """
    headers = {'Content-Type': 'application/json'}

    xis_response = requests.post(url=get_xis_metadata_api_endpoint(xis),
                                 data=renamed_data, headers=headers,
                                 auth=TokenAuth(), verify=False)
    return xis_response


def posting_supplemental_metadata_to_xis(xis, renamed_data):
    """This function post data to XIS and returns the XIS response to
            XIA load_target_metadata() """
    headers = {'Content-Type': 'application/json'}

    xis_response = requests.post(
        url=get_xis_supplemental_metadata_api_endpoint(xis), data=renamed_data,
        headers=headers, auth=TokenAuth(), verify=False)
    return xis_response


class TokenAuth(AuthBase):
    """Attaches HTTP Authentication Header to the given Request object."""

    def __call__(self, r, token_name='token'):
        # modify and return the request

        r.headers['Authorization'] = token_name + ' ' + \
            XISConfiguration.objects.first().xis_api_key
        return r
