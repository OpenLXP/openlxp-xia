
import logging

from ddt import ddt
from django.test import tag

from .test_setup import TestSetUp
from django_openlxp_xia.management.commands.transform_source_metadata import (
    get_target_metadata_for_transformation)
from django_openlxp_xia.models import (XIAConfiguration)
logger = logging.getLogger('dict_config_logger')


@tag('integration')
@ddt
class CommandIntegration(TestSetUp):
    # globally accessible data sets
    def test_get_target_metadata_for_transformation(self):
        """Test that get target mapping_dictionary from XIAConfiguration """
        xiaConfig = XIAConfiguration(
            target_metadata_schema='AGENT_p2881_target_metadata_schema.json')
        xiaConfig.save()
        source_target_mapping = get_target_metadata_for_transformation()
        self.assertTrue(source_target_mapping)
