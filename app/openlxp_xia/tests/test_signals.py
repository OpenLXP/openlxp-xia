from unittest.mock import patch

from django.test import tag

from openlxp_xia.models import MetadataFieldOverwrite, XIAConfiguration

from .test_setup import TestSetUp


@tag('unit')
class SignalTests(TestSetUp):

    def test_save_XIAConfiguration(self):
        """Test Retrieving list of field required to be overwritten"""
        with patch('openlxp_xia.signals.read_json_data',
                   return_value=self.target_data_dict):
            config = XIAConfiguration(publisher='source', xss_api='api',
                                      source_metadata_schema='',
                                      target_metadata_schema='',
                                      source_file='')
            config.save()
            return_val = MetadataFieldOverwrite.objects.values_list(
                "field_name", "field_type").first()

            self.assertTrue(return_val)
            self.assertEqual(return_val[0],
                             self.test_target_required_column_names[0])
