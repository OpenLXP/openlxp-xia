
import logging

from ddt import ddt
from django.test import tag

from openlxp_xia.management.utils.xis_client import \
    get_xis_metadata_api_endpoint
from openlxp_xia.models import XISConfiguration

from .test_setup import TestSetUp

logger = logging.getLogger('dict_config_logger')


@tag('integration')
@ddt
class CommandIntegration(TestSetUp):
    # globally accessible data sets
    def test_get_xis_metadata_api_endpoint(self):
        """Test that get target mapping_dictionary from XIAConfiguration """
        xisConfig = XISConfiguration(
            xis_metadata_api_endpoint='test_api')
        xisConfig.save()
        XIS_api = get_xis_metadata_api_endpoint()
        self.assertTrue(XIS_api)
