from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, tag

from openlxp_xia.models import XIAConfiguration


@tag('integration')
class ModelTests(TestCase):

    def test_create_two_xia_configuration(self):
        """Test that trying to create more than one XIA Configuration throws
        ValidationError """
        with patch('openlxp_xia.models.XIAConfiguration.field_overwrite'):
            with self.assertRaises(ValidationError):
                xiaConfig = XIAConfiguration(
                    publisher="XYZ",
                    source_metadata_schema="XYZ_source_validate_schema.json",
                    xss_api="https://localhost",
                    target_metadata_schema="p2881_schema.json")
                xiaConfig2 = XIAConfiguration(
                    publisher="ABC",
                    source_metadata_schema="ABC_source_validate_schema.json",
                    xss_api="https://localhost",
                    target_metadata_schema="p2881_schema.json")
                xiaConfig.save()
                xiaConfig2.save()
