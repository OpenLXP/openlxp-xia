import logging
from unittest.mock import patch

from ddt import ddt
from django.test import tag
from django.utils import timezone

from openlxp_xia.management.commands.load_target_metadata import (
    post_data_to_xis, rename_metadata_ledger_fields)
from openlxp_xia.management.commands.transform_source_metadata import (
    store_transformed_source_metadata, transform_source_using_key)
from openlxp_xia.management.commands.validate_source_metadata import (
    get_source_metadata_for_validation,
    store_source_metadata_validation_status, validate_source_using_key)
from openlxp_xia.management.commands.validate_target_metadata import (
    get_target_validation_schema, store_target_metadata_validation_status,
    validate_target_using_key)
from openlxp_xia.management.utils.xss_client import read_json_data
from openlxp_xia.models import (MetadataFieldOverwrite, MetadataLedger,
                                SupplementalLedger, XIAConfiguration,
                                XISConfiguration)

from .test_setup import TestSetUp

logger = logging.getLogger('dict_config_logger')


@tag('integration')
@ddt
class CommandIntegration(TestSetUp):
    # globally accessible data sets

    # Test cases for validate_source_metadata

    def test_get_source_metadata_for_validation(self):
        """Test retrieving  source metadata from MetadataLedger that
        needs to be validated"""

        metadata_ledger = MetadataLedger(
            record_lifecycle_status='Active',
            source_metadata=self.source_metadata,
            source_metadata_hash=self.hash_value,
            source_metadata_key=self.key_value,
            source_metadata_key_hash=self.key_value_hash,
            source_metadata_extraction_date=timezone.now())
        metadata_ledger.save()
        test_source_data = get_source_metadata_for_validation()
        self.assertTrue(test_source_data)

    def test_validate_source_using_key(self):
        """Test to check validation process for source"""

        recommended_column_name = []
        metadata_ledger = MetadataLedger(
            record_lifecycle_status='Active',
            source_metadata=self.source_metadata,
            source_metadata_hash=self.hash_value,
            source_metadata_key=self.key_value,
            source_metadata_key_hash=self.key_value_hash,
            source_metadata_extraction_date=timezone.now())
        metadata_ledger_invalid = MetadataLedger(
            record_lifecycle_status='Active',
            source_metadata=self.metadata_invalid,
            source_metadata_hash=self.hash_value_invalid,
            source_metadata_key=self.key_value_invalid,
            source_metadata_key_hash=self.key_value_hash_invalid,
            source_metadata_extraction_date=timezone.now())
        metadata_ledger.save()
        metadata_ledger_invalid.save()
        result_test_query = MetadataLedger.objects. \
            values('source_metadata_key_hash', 'source_metadata')
        validate_source_using_key(result_test_query,
                                  self.test_required_column_names,
                                  recommended_column_name)
        result_query = MetadataLedger.objects. \
            values('source_metadata_validation_status',
                   'record_lifecycle_status'). \
            filter(source_metadata_key=self.key_value).first()
        result_query_invalid = MetadataLedger.objects. \
            values('source_metadata_validation_status',
                   'record_lifecycle_status'). \
            filter(source_metadata_key=self.key_value_invalid).first()
        self.assertEqual('Y',
                         result_query['source_metadata_validation_status'])
        self.assertEqual('Active',
                         result_query['record_lifecycle_status'])
        self.assertEqual('N', result_query_invalid[
            'source_metadata_validation_status'])

    def test_store_source_metadata_validation_status_valid(self):
        """Test to store validation status for valid source metadata
            in metadata ledger """

        metadata_ledger = MetadataLedger(
            source_metadata=self.source_metadata,
            source_metadata_key_hash=self.key_value_hash,
            source_metadata_key=self.key_value)
        metadata_ledger.save()
        store_source_metadata_validation_status(MetadataLedger.objects.
                                                values('source_metadata'),
                                                self.key_value_hash,
                                                'Y', 'Active',
                                                MetadataLedger.objects.
                                                values('source_metadata')
                                                )
        result_query = MetadataLedger.objects.values(
            'source_metadata_validation_status',
            'source_metadata_validation_date',
            'record_lifecycle_status').filter(
            source_metadata_key_hash=self.key_value_hash).first()

        self.assertTrue(result_query.get('source_metadata_validation_date'))
        self.assertEqual("Y", result_query.get(
            'source_metadata_validation_status'))
        self.assertEqual('Active', result_query.get(
            'record_lifecycle_status'))

    def test_store_source_metadata_validation_status_invalid(self):
        """Test to store validation status for invalid source metadata
            in metadata ledger """

        metadata_ledger = MetadataLedger(
            source_metadata=self.source_metadata,
            source_metadata_key_hash=self.key_value_hash,
            source_metadata_key=self.key_value)
        metadata_ledger.save()
        store_source_metadata_validation_status(MetadataLedger.objects.
                                                values('source_metadata'),
                                                self.key_value_hash,
                                                'N', 'Inactive',
                                                MetadataLedger.objects.
                                                values('source_metadata')
                                                )
        result_query = MetadataLedger.objects.values(
            'metadata_record_inactivation_date',
            'source_metadata_validation_status',
            'source_metadata_validation_date',
            'record_lifecycle_status').filter(
            source_metadata_key_hash=self.key_value_hash).first()

        self.assertTrue(result_query.get('source_metadata_validation_date'))
        self.assertTrue(result_query.get('metadata_record_inactivation_date'))
        self.assertEqual("N", result_query.get(
            'source_metadata_validation_status'))
        self.assertEqual('Inactive', result_query.get(
            'record_lifecycle_status'))

    # Test cases for transform_source_metadata

    def test_transform_source_using_key_overwrite(self):
        """Test to transform source metadata to target metadata schema
        format"""
        metadata_ledger = MetadataLedger(
            record_lifecycle_status='Active',
            source_metadata=self.source_metadata_overwrite,
            source_metadata_key_hash=self.key_value_hash_overwrite,
            source_metadata_validation_status='Y',
            source_metadata_key=self.key_value_overwrite,
            source_metadata_validation_date=timezone.now(),
            source_metadata_extraction_date=timezone.now())
        metadata_ledger.save()

        test_data_dict = MetadataLedger.objects.values(
            'source_metadata').filter(
            source_metadata_validation_status='Y',
            record_lifecycle_status='Active').exclude(
            source_metadata_validation_date=None)

        test_metadata_overwrite = \
            MetadataFieldOverwrite(field_name='test_name', field_type='char',
                                   field_value='new_value', overwrite=True)
        test_metadata_overwrite.save()
        transform_source_using_key(test_data_dict, self.source_target_mapping,
                                   self.test_required_column_names,
                                   self.expected_datatype)

        result_data = MetadataLedger.objects.filter(
            source_metadata_key=self.key_value_overwrite,
            record_lifecycle_status='Active',
            source_metadata_validation_status='Y'
        ).values(
            'source_metadata_transformation_date',
            'target_metadata_key',
            'target_metadata_key_hash',
            'target_metadata',
            'target_metadata_hash').first()

        result_data_supplemental = SupplementalLedger.objects.filter(
            supplemental_metadata_key=self.key_value_overwrite,
            record_lifecycle_status='Active',
        ).values(
            'supplemental_metadata_transformation_date',
            'supplemental_metadata_key',
            'supplemental_metadata_key_hash',
            'supplemental_metadata',
            'supplemental_metadata_hash').first()

        self.assertTrue(result_data.get('source_metadata_transformation_date'))
        self.assertTrue(result_data.get('target_metadata_key'))
        self.assertTrue(result_data.get('target_metadata_key_hash'))
        self.assertTrue(result_data.get('target_metadata'))
        self.assertTrue(result_data.get('target_metadata_hash'))
        self.assertTrue(result_data_supplemental.
                        get('supplemental_metadata_transformation_date'))
        self.assertTrue(result_data_supplemental.
                        get('supplemental_metadata_key'))
        self.assertTrue(result_data_supplemental.
                        get('supplemental_metadata_key_hash'))
        self.assertTrue(result_data_supplemental.
                        get('supplemental_metadata'))
        self.assertTrue(result_data_supplemental.
                        get('supplemental_metadata_hash'))

    def test_transform_source_using_key(self):
        """Test to transform source metadata to target metadata schema
        format"""
        metadata_ledger = MetadataLedger(
            record_lifecycle_status='Active',
            source_metadata=self.source_metadata,
            source_metadata_key_hash=self.key_value_hash,
            source_metadata_validation_status='Y',
            source_metadata_key=self.key_value,
            source_metadata_validation_date=timezone.now(),
            source_metadata_extraction_date=timezone.now())
        metadata_ledger.save()

        test_data_dict = MetadataLedger.objects.values(
            'source_metadata').filter(
            source_metadata_validation_status='Y',
            record_lifecycle_status='Active').exclude(
            source_metadata_validation_date=None)

        transform_source_using_key(test_data_dict, self.source_target_mapping,
                                   self.test_required_column_names,
                                   self.expected_datatype)

        result_data = MetadataLedger.objects.filter(
            source_metadata_key=self.key_value,
            record_lifecycle_status='Active',
            source_metadata_validation_status='Y'
        ).values(
            'source_metadata_transformation_date',
            'target_metadata_key',
            'target_metadata_key_hash',
            'target_metadata',
            'target_metadata_hash').first()

        result_data_supplemental = SupplementalLedger.objects.filter(
            supplemental_metadata_key=self.key_value,
            record_lifecycle_status='Active',
        ).values(
            'supplemental_metadata_transformation_date',
            'supplemental_metadata_key',
            'supplemental_metadata_key_hash',
            'supplemental_metadata',
            'supplemental_metadata_hash').first()

        self.assertTrue(result_data.get('source_metadata_transformation_date'))
        self.assertTrue(result_data.get('target_metadata_key'))
        self.assertTrue(result_data.get('target_metadata_key_hash'))
        self.assertTrue(result_data.get('target_metadata'))
        self.assertTrue(result_data.get('target_metadata_hash'))
        self.assertTrue(result_data_supplemental.
                        get('supplemental_metadata_transformation_date'))
        self.assertTrue(result_data_supplemental.
                        get('supplemental_metadata_key'))
        self.assertTrue(result_data_supplemental.
                        get('supplemental_metadata_key_hash'))
        self.assertTrue(result_data_supplemental.
                        get('supplemental_metadata'))
        self.assertTrue(result_data_supplemental.
                        get('supplemental_metadata_hash'))

    def test_store_transformed_source_metadata(self):
        """Test to store transformed metadata and
        supplemental metadata in metadata ledger """

        metadata_ledger = MetadataLedger(
            source_metadata=self.source_metadata,
            source_metadata_key_hash=self.key_value_hash,
            source_metadata_validation_status='Y',
            record_lifecycle_status='Active',
            source_metadata_extraction_date=timezone.now()
        )
        metadata_ledger.save()

        store_transformed_source_metadata(self.key_value, self.key_value_hash,
                                          self.target_metadata,
                                          self.hash_value,
                                          self.supplemental_data
                                          )

        result_query = MetadataLedger.objects.values(
            'source_metadata_transformation_date',
            'target_metadata_key_hash',
            'target_metadata', 'target_metadata_hash').filter(
            target_metadata_key_hash=self.key_value_hash).first()

        result_query_supplemental = SupplementalLedger.objects.values(
            'supplemental_metadata_key_hash',
            'supplemental_metadata_transformation_date',
            'supplemental_metadata').filter(
            supplemental_metadata_key_hash=self.key_value_hash).first()

        self.assertTrue(result_query_supplemental.
                        get('supplemental_metadata_transformation_date'))
        self.assertEqual(self.key_value_hash, result_query_supplemental.get(
            'supplemental_metadata_key_hash'))
        self.assertEqual(self.supplemental_data, result_query_supplemental.get(
            'supplemental_metadata'))

        self.assertTrue(result_query.
                        get('source_metadata_transformation_date'))
        self.assertEqual(self.key_value_hash, result_query.get(
            'target_metadata_key_hash'))
        self.assertEqual(self.target_metadata, result_query.get(
            'target_metadata'))
        self.assertEqual(self.hash_value, result_query.get(
            'target_metadata_hash'))

    # Test cases for validate_target_metadata

    def test_get_target_validation_schema(self):
        """Test to retrieve source validation schema from XIA configuration """
        with patch('openlxp_xia.models.XIAConfiguration.field_overwrite'):
            xiaConfig = XIAConfiguration(
                target_metadata_schema='p2881_target_validation_schema.json')
            xiaConfig.save()
            result_dict = get_target_validation_schema()
            expected_dict = \
                read_json_data('xss', 'p2881_target_validation_schema.json')
            self.assertEqual(expected_dict, result_dict)

    def test_validate_target_using_key(self):
        """Test for Validating target data for required columns """
        metadata_ledger = MetadataLedger(
            record_lifecycle_status='Active',
            source_metadata=self.source_metadata,
            target_metadata=self.target_metadata,
            target_metadata_hash=self.target_hash_value,
            target_metadata_key_hash=self.target_key_value_hash,
            target_metadata_key=self.target_key_value,
            source_metadata_transformation_date=timezone.now())
        metadata_ledger.save()
        metadata_ledger_invalid = MetadataLedger(
            record_lifecycle_status='Active',
            source_metadata=self.metadata_invalid,
            target_metadata=self.target_metadata_invalid,
            target_metadata_hash=self.target_hash_value_invalid,
            target_metadata_key_hash=self.target_key_value_hash_invalid,
            target_metadata_key=self.target_key_value_invalid,
            source_metadata_transformation_date=timezone.now())
        metadata_ledger_invalid.save()
        test_data = MetadataLedger.objects.values('target_metadata_key_hash',
                                                  'target_metadata').filter(
            target_metadata_validation_status='',
            record_lifecycle_status='Active'
        ).exclude(
            source_metadata_transformation_date=None)

        validate_target_using_key(
            test_data, self.test_target_required_column_names,
            self.recommended_column_name, self.expected_datatype)
        result_query = MetadataLedger.objects.values(
            'target_metadata_validation_status', 'record_lifecycle_status'). \
            filter(target_metadata_key_hash=self.target_key_value_hash).first()

        result_query_invalid = MetadataLedger.objects.values(
            'target_metadata_validation_status', 'record_lifecycle_status'). \
            filter(target_metadata_key_hash=self.
                   target_key_value_hash_invalid).first()
        self.assertEqual('Y', result_query.get(
            'target_metadata_validation_status'))
        self.assertEqual('Active', result_query.get(
            'record_lifecycle_status'))
        self.assertEqual('N', result_query_invalid.get(
            'target_metadata_validation_status'))
        # self.assertEqual('Inactive', result_query_invalid.get(
        #     'record_lifecycle_status'))

    def test_store_target_metadata_validation_status_valid(self):
        """Test to store validation status for valid target metadata
        in metadata ledger """

        metadata_ledger = MetadataLedger(
            source_metadata=self.source_metadata,
            target_metadata=self.target_metadata,
            target_metadata_key_hash=self.key_value_hash)
        metadata_ledger.save()

        supplemental_ledger = SupplementalLedger(
            supplemental_metadata={"key": "value"},
            supplemental_metadata_key_hash=self.key_value_hash)
        supplemental_ledger.save()
        store_target_metadata_validation_status(MetadataLedger.objects.
                                                values('target_metadata'),
                                                self.key_value_hash,
                                                'Y', 'Active', MetadataLedger.
                                                objects.
                                                values('target_metadata')
                                                )
        result_query = MetadataLedger.objects.values(
            'target_metadata_validation_status',
            'target_metadata_validation_date',
            'record_lifecycle_status').filter(
            target_metadata_key_hash=self.key_value_hash).first()

        result_query_supplemental = SupplementalLedger.objects.values(
            'supplemental_metadata_validation_date').filter(
            supplemental_metadata_key_hash=self.key_value_hash).first()

        self.assertTrue(result_query_supplemental.
                        get('supplemental_metadata_validation_date'))
        self.assertEqual("Y", result_query.get(
            'target_metadata_validation_status'))
        self.assertEqual('Active', result_query.get(
            'record_lifecycle_status'))

    def test_store_target_metadata_validation_status_invalid(self):
        """Test to store validation status for invalid target metadata
        in metadata ledger """

        metadata_ledger = MetadataLedger(
            source_metadata=self.source_metadata,
            target_metadata=self.target_metadata,
            target_metadata_key_hash=self.key_value_hash)
        metadata_ledger.save()
        supplemental_ledger = SupplementalLedger(
            supplemental_metadata={"key": "value"},
            supplemental_metadata_key_hash=self.key_value_hash)
        supplemental_ledger.save()
        store_target_metadata_validation_status(MetadataLedger.objects.
                                                values('target_metadata'),
                                                self.key_value_hash,
                                                'N', 'Inactive',
                                                MetadataLedger.objects.
                                                values('target_metadata')
                                                )
        result_query = MetadataLedger.objects.values(
            'metadata_record_inactivation_date',
            'target_metadata_validation_status',
            'target_metadata_validation_date',
            'record_lifecycle_status').filter(
            target_metadata_key_hash=self.key_value_hash).first()

        result_query_supplemental = SupplementalLedger.objects.values(
            'supplemental_metadata_validation_date').filter(
            supplemental_metadata_key_hash=self.key_value_hash).first()

        self.assertTrue(result_query_supplemental.
                        get('supplemental_metadata_validation_date'))
        self.assertTrue(result_query.get('target_metadata_validation_date'))
        self.assertTrue(result_query.get('metadata_record_inactivation_date'))
        self.assertEqual("N", result_query.get(
            'target_metadata_validation_status'))
        self.assertEqual('Inactive', result_query.get(
            'record_lifecycle_status'))

    # Test cases for load_target_metadata

    def test_rename_metadata_ledger_fields(self):
        """Test for Renaming XIA column names to match with XIS column names"""
        with patch('openlxp_xia.models.XIAConfiguration.field_overwrite'):
            xiaConfig = XIAConfiguration(publisher='AGENT')
            xiaConfig.save()

            return_data = rename_metadata_ledger_fields(self.xia_data)
            self.assertEquals(self.xis_expected_data['metadata_hash'],
                              return_data['metadata_hash'])
            self.assertEquals(self.xis_expected_data['metadata_key'],
                              return_data['metadata_key'])
            self.assertEquals(self.xis_expected_data['metadata_key_hash'],
                              return_data['metadata_key_hash'])
            self.assertEquals(self.xis_expected_data['provider_name'],
                              return_data['provider_name'])

    def test_post_data_to_xis_response_201(self):
        """POSTing XIA metadata_ledger to XIS metadata_ledger and receive
        response status code 201"""
        with patch('openlxp_xia.models.XIAConfiguration.field_overwrite'):
            metadata_ledger = MetadataLedger(
                record_lifecycle_status='Active',
                source_metadata=self.source_metadata,
                target_metadata=self.target_metadata,
                target_metadata_hash=self.target_hash_value,
                target_metadata_key_hash=self.target_key_value_hash,
                target_metadata_key=self.target_key_value,
                source_metadata_transformation_date=timezone.now(),
                target_metadata_validation_status='Y',
                source_metadata_validation_status='Y',
                target_metadata_transmission_status='Ready')
            metadata_ledger.save()
            input_data = MetadataLedger.objects.filter(
                record_lifecycle_status='Active',
                target_metadata_validation_status='Y',
                target_metadata_transmission_status='Ready').values(
                'metadata_record_uuid',
                'target_metadata',
                'target_metadata_hash',
                'target_metadata_key',
                'target_metadata_key_hash')
            xiaConfig = XIAConfiguration(publisher='AGENT')
            xiaConfig.save()
            xisConfig = XISConfiguration(
                xis_metadata_api_endpoint=self.xis_api_endpoint_url)
            xisConfig.save()
            with patch('requests.post') as response_obj:
                response_obj.return_value = response_obj
                response_obj.status_code = 201

                post_data_to_xis(input_data)
                result_query = MetadataLedger.objects.values(
                    'target_metadata_transmission_status_code',
                    'target_metadata_transmission_status').filter(
                    target_metadata_key=self.target_key_value).first()

                self.assertEqual(201, result_query.get(
                    'target_metadata_transmission_status_code'))
                self.assertEqual('Successful', result_query.get(
                    'target_metadata_transmission_status'))

    def test_post_data_to_xis_responses_other_than_201(self):
        """POSTing XIA metadata_ledger to XIS metadata_ledger and receive
        response status code 201"""
        with patch('openlxp_xia.models.XIAConfiguration.field_overwrite'):
            metadata_ledger = MetadataLedger(
                record_lifecycle_status='Active',
                source_metadata=self.source_metadata,
                target_metadata=self.target_metadata,
                target_metadata_hash=self.target_hash_value,
                target_metadata_key_hash=self.target_key_value_hash,
                target_metadata_key=self.target_key_value,
                source_metadata_transformation_date=timezone.now(),
                target_metadata_validation_status='Y',
                source_metadata_validation_status='Y',
                target_metadata_transmission_status='Ready')
            metadata_ledger.save()
            input_data = MetadataLedger.objects.filter(
                record_lifecycle_status='Active',
                target_metadata_validation_status='Y',
                target_metadata_transmission_status='Ready').values(
                'metadata_record_uuid',
                'target_metadata',
                'target_metadata_hash',
                'target_metadata_key',
                'target_metadata_key_hash')
            xiaConfig = XIAConfiguration(publisher='AGENT')
            xiaConfig.save()
            xisConfig = XISConfiguration(
                xis_metadata_api_endpoint=self.xis_api_endpoint_url)
            xisConfig.save()
            with patch('requests.post') as response_obj:
                response_obj.return_value = response_obj
                response_obj.status_code = 400
                post_data_to_xis(input_data)
                result_query = MetadataLedger.objects.values(
                    'target_metadata_transmission_status_code',
                    'target_metadata_transmission_status').filter(
                    target_metadata_key=self.target_key_value).first()
                self.assertEqual(400, result_query.get(
                    'target_metadata_transmission_status_code'))
                self.assertEqual('Failed', result_query.get(
                    'target_metadata_transmission_status'))
