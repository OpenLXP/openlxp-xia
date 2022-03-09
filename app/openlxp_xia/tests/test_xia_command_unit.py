import logging
from unittest.mock import patch

from ddt import ddt
from django.test import tag
from django.utils import timezone

from openlxp_xia.management.commands.load_supplemental_metadata import (
    load_supplemental_metadata_to_xis, post_supplemental_metadata_to_xis,
    rename_supplemental_metadata_fields)
from openlxp_xia.management.commands.load_target_metadata import (
    get_records_to_load_into_xis, post_data_to_xis,
    rename_metadata_ledger_fields)
from openlxp_xia.management.commands.transform_source_metadata import (
    create_supplemental_metadata, create_target_metadata_dict,
    get_metadata_fields_to_overwrite, get_source_metadata_for_transformation,
    overwrite_append_metadata, overwrite_metadata_field,
    transform_source_using_key, type_checking_target_metadata)
from openlxp_xia.management.commands.validate_source_metadata import (
    get_source_metadata_for_validation, validate_source_using_key,
    store_source_metadata_validation_status)
from openlxp_xia.management.commands.validate_target_metadata import (
    get_target_metadata_for_validation, update_previous_instance_in_metadata,
    validate_target_using_key)
from openlxp_xia.models import (MetadataFieldOverwrite, MetadataLedger,
                                SupplementalLedger, XIAConfiguration,
                                XISConfiguration)

from .test_setup import TestSetUp

logger = logging.getLogger('dict_config_logger')


@tag('unit')
@ddt
class CommandTests(TestSetUp):

    # Test cases for validate_source_metadata

    def test_get_source_metadata_for_validation(self):
        """Test to Retrieving source metadata from MetadataLedger that needs
        to be validated"""
        with patch('openlxp_xia.management.commands.'
                   'validate_source_metadata.MetadataLedger.objects') \
                as meta_obj:
            meta_ledger = MetadataLedger.objects.values(
                source_metadata=self.source_metadata).filter(
                source_metadata_validation_status='',
                record_lifecycle_status='Active').exclude(
                source_metadata_extraction_date=None)
            meta_obj.first.return_value = meta_ledger
            return_from_function = get_source_metadata_for_validation()
            self.assertEqual(meta_obj.first.return_value, return_from_function)

    def test_validate_source_using_key_more_than_one(self):
        """Test to Validating source data against required & recommended
        column names for more than one row"""
        data = [{'source_metadata_key_hash': 123,
                 'source_metadata': self.source_metadata},
                {'source_metadata_key_hash': 123,
                 'source_metadata': self.source_metadata}]

        recommended_column_name = []
        with patch('openlxp_xia.management.commands.'
                   'validate_source_metadata'
                   '.store_source_metadata_validation_status',
                   return_value=None) as mock_store_source_valid_status:
            validate_source_using_key(data, self.test_required_column_names,
                                      recommended_column_name)
            self.assertEqual(
                mock_store_source_valid_status.call_count, 2)

    def test_validate_source_using_key_more_than_zero(self):
        """Test to Validating source data against required/ recommended column
            names with no data"""
        data = []
        recommended_column_name = []
        with patch('openlxp_xia.management.commands.'
                   'validate_source_metadata'
                   '.store_source_metadata_validation_status',
                   return_value=None) as mock_store_source_valid_status:
            validate_source_using_key(data, self.test_required_column_names,
                                      recommended_column_name)
            self.assertEqual(
                mock_store_source_valid_status.call_count, 0)

    def test_store_source_metadata_validation_status_valid(self):
        """Test to store source metadata with validation details"""

        metadata_ledger = MetadataLedger(
            record_lifecycle_status='Active',
            source_metadata=self.source_metadata,
            source_metadata_hash=self.hash_value,
            source_metadata_key=self.key_value,
            source_metadata_key_hash=self.key_value_hash,
            source_metadata_extraction_date=timezone.now())
        metadata_ledger.save()

        source_data_dict = \
            MetadataLedger.objects.values('source_metadata_key_hash',
                                          'source_metadata').filter(
                source_metadata_validation_status='',
                record_lifecycle_status='Active').exclude(
                source_metadata_extraction_date=None)

        store_source_metadata_validation_status(
            source_data_dict, self.key_value_hash, 'Y',
            'Active', self.source_metadata)

        result_metadata = \
            MetadataLedger.objects.values(
                "source_metadata_validation_status",
                "source_metadata_validation_date").filter(
                source_metadata_key_hash=self.key_value_hash,
                record_lifecycle_status='Active').first()

        self.assertEqual('Y',
                         result_metadata['source_metadata_validation_status'])
        self.assertTrue(result_metadata['source_metadata_validation_date'])

    def test_store_source_metadata_validation_status_invalid(self):
        """Test to store source metadata with validation details"""

        metadata_ledger = MetadataLedger(
            record_lifecycle_status='Active',
            source_metadata=self.source_metadata,
            source_metadata_hash=self.hash_value,
            source_metadata_key=self.key_value,
            source_metadata_key_hash=self.key_value_hash,
            source_metadata_extraction_date=timezone.now())
        metadata_ledger.save()

        source_data_dict = \
            MetadataLedger.objects.values('source_metadata_key_hash',
                                          'source_metadata').filter(
                source_metadata_validation_status='',
                record_lifecycle_status='Active').exclude(
                source_metadata_extraction_date=None)

        store_source_metadata_validation_status(
            source_data_dict, self.key_value_hash, 'N',
            'Inactive', self.source_metadata)

        result_metadata = \
            MetadataLedger.objects.values(
                "source_metadata_validation_status",
                "source_metadata_validation_date",
                "metadata_record_inactivation_date").filter(
                source_metadata_key_hash=self.key_value_hash).first()

        self.assertEqual('N',
                         result_metadata['source_metadata_validation_status'])
        self.assertTrue(result_metadata['source_metadata_validation_date'])
        self.assertTrue(result_metadata['metadata_record_inactivation_date'])

    # Test cases for transform_source_metadata

    def test_type_checking_target_metadata(self):
        """"Test function for type checking and explicit type conversion of
        metadata """
        target_metadata = {
            0: self.target_metadata}
        target_metadata = type_checking_target_metadata(1, target_metadata,
                                                        self.expected_datatype)
        self.assertIsInstance(target_metadata[0]['General_Information'][
                                  "EndDate"], str)

    def test_get_source_metadata_for_transformation(self):
        """Test to Retrieving Source metadata from MetadataLedger that needs
        to be transformed"""
        with patch('openlxp_xia.management.commands.'
                   'transform_source_metadata'
                   '.MetadataLedger.objects') as meta_obj:
            target_data_dict = MetadataLedger.objects.values(
                source_data_dict=self.source_metadata).filter(
                source_metadata_validation_status='Y',
                record_lifecycle_status='Active').exclude(
                source_metadata_validation_date=None)
            meta_obj.first.return_value = target_data_dict
            return_from_function = get_source_metadata_for_transformation()
            self.assertEqual(meta_obj.first.return_value,
                             return_from_function)

    def test_create_supplemental_data(self):
        """Test to check creation of supplemental data from source data"""

        supplemental_data = \
            create_supplemental_metadata(self.test_metadata_column_list,
                                         self.
                                         source_metadata_with_supplemental)
        self.assertEqual(supplemental_data, self.supplemental_data)

    def test_create_target_metadata_dict(self):
        """Test for a function to replace and transform source data to target
        data for using target mapping schema"""
        expected_data_dict = {0: self.target_metadata}
        with patch('openlxp_xia.management.utils.xia_internal.'
                   'dict_flatten', return_value=self.source_metadata), \
                patch('openlxp_xia.management.commands.'
                      'transform_source_metadata.create_supplemental_metadata',
                      return_value=None):
            result_data_dict, supplemental_data = create_target_metadata_dict(
                1, self.source_target_mapping, self.source_metadata,
                self.test_required_column_names, self.expected_datatype)
            self.assertEqual(result_data_dict[0]['Course'].get('CourseCode'),
                             expected_data_dict[0]['Course'].get('CourseCode'))
            self.assertEqual(
                result_data_dict[0]['Course'].get('CourseProviderName'),
                expected_data_dict[0]['Course'].get('CourseProviderName'))

    def test_transform_source_using_key_more_zero(self):
        """Test for transforming source data using target metadata schema
        with no data"""
        data = []
        with patch('openlxp_xia.management.utils.xia_internal'
                   '.get_target_metadata_key_value',
                   return_value=None), \
                patch('openlxp_xia.management.commands.'
                      'transform_source_metadata'
                      '.store_transformed_source_metadata',
                      return_value=None) as mock_store_transformed_source:
            mock_store_transformed_source.return_value = \
                mock_store_transformed_source
            mock_store_transformed_source.exclude.return_value = \
                mock_store_transformed_source
            mock_store_transformed_source.filter.side_effect = [
                mock_store_transformed_source, mock_store_transformed_source]

            transform_source_using_key(data, self.source_target_mapping,
                                       self.test_required_column_names,
                                       self.expected_datatype)

            self.assertEqual(
                mock_store_transformed_source.call_count, 0)

    def test_transform_source_using_key_more_than_one(self):
        """Test for transforming source data using target metadata schema for
        more than one row"""
        data = [{0: self.source_metadata},
                {1: self.source_metadata}]
        with patch('openlxp_xia.management.utils.xia_internal'
                   '.get_target_metadata_key_value',
                   return_value=None), \
                patch('openlxp_xia.management.commands.'
                      'transform_source_metadata'
                      '.store_transformed_source_metadata',
                      return_value=None) as mock_store_transformed_source:
            mock_store_transformed_source.return_value = \
                mock_store_transformed_source
            mock_store_transformed_source.exclude.return_value = \
                mock_store_transformed_source
            mock_store_transformed_source.filter.side_effect = [
                mock_store_transformed_source, mock_store_transformed_source]

            transform_source_using_key(data, self.source_target_mapping,
                                       self.test_required_column_names,
                                       self.expected_datatype)

            self.assertEqual(
                mock_store_transformed_source.call_count, 2)

    def test_overwrite_metadata_field(self):
        """Test to overwrite metadata with admin entered values and
        return metadata in dictionary format """

        with patch('openlxp_xia.management.commands.transform_source_metadata'
                   '.get_metadata_fields_to_overwrite') as mock_get_overwrite:
            mock_get_overwrite.return_value = self.metadata_df

            return_val = overwrite_metadata_field(self.metadata_df)
            self.assertIsInstance(return_val, dict)

    def test_get_metadata_fields_to_overwrite(self):
        """Test for looping through fields to be overwrite or appended"""
        with patch('openlxp_xia.management.commands.'
                   'transform_source_metadata.MetadataFieldOverwrite.'
                   'objects') as mock_field, \
                patch('openlxp_xia.management.commands.'
                      'transform_source_metadata.'
                      'overwrite_append_metadata') as mock_overwrite_fun:
            config = \
                [MetadataFieldOverwrite(field_name='column1', overwrite=True,
                                        field_value='value1'),
                 MetadataFieldOverwrite(field_name='column2', overwrite=False,
                                        field_value='value2')]
            mock_field.all.return_value = config
            mock_overwrite_fun.return_value = self.metadata_df

            get_metadata_fields_to_overwrite(self.metadata_df)
            self.assertEqual(mock_overwrite_fun.call_count, 2)

    def test_overwrite_append_metadata(self):
        """test Overwrite & append metadata fields based on overwrite flag """
        return_val = \
            overwrite_append_metadata(self.metadata_df, 'column_1', 'value_1',
                                      True)

        self.assertEqual(return_val['column_1'][0], 'value_1')

    # Test cases for validate_target_metadata

    def test_get_target_metadata_for_validation(self):
        """Test to Retrieving target metadata from MetadataLedger that needs
        to be validated"""
        with patch('openlxp_xia.management.commands.'
                   'validate_target_metadata.MetadataLedger.objects') \
                as meta_obj:
            target_data_dict = MetadataLedger.objects.values(
                target_metadata=self.target_metadata).filter(
                target_metadata_validation_status='',
                record_lifecycle_status='Active').exclude(
                source_metadata_transformation_date=None)
            meta_obj.first.return_value = target_data_dict
            return_from_function = get_target_metadata_for_validation()
            self.assertEqual(meta_obj.first.return_value,
                             return_from_function)

    def test_validate_target_using_key_more_than_one(self):
        """Test to Validating target data against required & recommended
        column names for more than one row"""
        data = [{'target_metadata_key_hash': 123,
                 'target_metadata': self.target_metadata},
                {'target_metadata_key_hash': 123,
                 'target_metadata': self.target_metadata}]
        test_required_column_names = {
            'CourseInstance.EndDate', 'CourseInstance.DeliveryMode',
            'CourseInstance.CourseCode', 'CourseInstance.Instructor',
            'Course.CourseProviderName', 'Course.CourseDescription',
            'Course.CourseShortDescription', 'CourseInstance.StartDate',
            'Course.CourseCode', 'CourseInstance.CourseTitle ',
            'General_Information.StartDate', 'Course.CourseSubjectMatter',
            'General_Information.EndDate', 'Course.CourseTitle',
            'Technical.CourseTitle'}
        recommended_column_name = {'Technical_Information.Thumbnail',
                                   'CourseInstance.Thumbnail'}
        with patch('openlxp_xia.management.commands.'
                   'validate_target_metadata'
                   '.store_target_metadata_validation_status',
                   return_value=None) as mock_store_target_valid_status:
            validate_target_using_key(data, test_required_column_names,
                                      recommended_column_name,
                                      self.expected_datatype)
            self.assertEqual(
                mock_store_target_valid_status.call_count, 2)

    def test_validate_target_using_key_zero(self):
        """Validating target data against required & recommended column names
        with no data"""

        data = []

        with patch('openlxp_xia.management.commands.'
                   'validate_target_metadata'
                   '.store_target_metadata_validation_status',
                   return_value=None) as mock_store_target_valid_status:
            validate_target_using_key(data,
                                      self.test_target_required_column_names,
                                      self.recommended_column_name,
                                      self.expected_datatype)

            self.assertEqual(mock_store_target_valid_status.call_count, 0)

    def test_update_previous_instance_in_metadata(self):
        """test to check Update older instances of record to inactive status"""
        metadata = MetadataLedger(source_metadata=self.source_metadata,
                                  target_metadata=self.target_metadata,
                                  target_metadata_key=self.target_key_value,
                                  target_metadata_key_hash=self.
                                  target_key_value_hash,
                                  source_metadata_key_hash=self.
                                  target_key_value_hash,
                                  target_metadata_hash=self.target_hash_value,
                                  record_lifecycle_status='Active',
                                  target_metadata_validation_date=timezone.
                                  now())
        metadata.save()
        update_previous_instance_in_metadata(self.key_value_hash)

        updated_value = MetadataLedger.objects. \
            get(target_metadata_key_hash=self.target_key_value_hash)
        self.assertEqual(updated_value.record_lifecycle_status, 'Inactive')

    # Test cases for load_target_metadata

    def test_rename_metadata_ledger_fields(self):
        """Test for Renaming XIA column names to match with XIS column names"""
        with patch('openlxp_xia.management.utils.xia_internal'
                   '.get_publisher_detail'), \
                patch('openlxp_xia.management.utils.xia_internal'
                      '.XIAConfiguration.objects') as xisCfg:
            xiaConfig = XIAConfiguration(publisher='AGENT')
            xisCfg.first.return_value = xiaConfig
            return_data = rename_metadata_ledger_fields(self.xia_data)
            self.assertEquals(self.xis_expected_data['metadata_hash'],
                              return_data['metadata_hash'])
            self.assertEquals(self.xis_expected_data['metadata_key'],
                              return_data['metadata_key'])
            self.assertEquals(self.xis_expected_data['metadata_key_hash'],
                              return_data['metadata_key_hash'])
            self.assertEquals(self.xis_expected_data['provider_name'],
                              return_data['provider_name'])

    def test_get_records_to_load_into_xis_one_record(self):
        """Test to Retrieve number of Metadata_Ledger records in XIA to load
        into XIS  and calls the post_data_to_xis accordingly"""
        with patch('openlxp_xia.management.commands.'
                   'load_target_metadata.post_data_to_xis', return_value=None
                   )as mock_post_data_to_xis, \
                patch('openlxp_xia.management.commands.load_target_metadata.'
                      'MetadataLedger.objects') as meta_obj:
            meta_data = MetadataLedger(
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
            meta_obj.return_value = meta_obj
            meta_obj.exclude.return_value = meta_obj
            meta_obj.values.return_value = [meta_data]
            meta_obj.filter.side_effect = [meta_obj, meta_obj]
            get_records_to_load_into_xis()
            self.assertEqual(
                mock_post_data_to_xis.call_count, 1)

    def test_get_records_to_load_into_xis_zero(self):
        """Test to Retrieve number of Metadata_Ledger records in XIA to load
        into XIS  and calls the post_data_to_xis accordingly"""
        with patch(
                'openlxp_xia.management.commands.load_target_metadata'
                '.post_data_to_xis', return_value=None)as \
                mock_post_data_to_xis, \
                patch(
                    'openlxp_xia.management.commands.'
                    'load_target_metadata.MetadataLedger.objects') as meta_obj:
            meta_obj.return_value = meta_obj
            meta_obj.exclude.return_value = meta_obj
            meta_obj.filter.side_effect = [meta_obj, meta_obj]
            get_records_to_load_into_xis()
            self.assertEqual(
                mock_post_data_to_xis.call_count, 0)

    def test_post_data_to_xis_zero(self):
        """Test for POSTing XIA metadata_ledger to XIS metadata_ledger
        when data is not present"""
        data = []
        with patch('openlxp_xia.management.commands'
                   '.load_target_metadata.rename_metadata_ledger_fields',
                   return_value=self.xis_expected_data), \
                patch('openlxp_xia.management.utils.xia_internal'
                      '.get_publisher_detail'), \
                patch('openlxp_xia.management.utils.xia_internal'
                      '.XIAConfiguration.objects') as xiaCfg, \
                patch('openlxp_xia.management.commands.load_target_metadata.'
                      'MetadataLedger.objects') as meta_obj, \
                patch('requests.post') as response_obj, \
                patch(
                    'openlxp_xia.management.commands.'
                    'load_target_metadata'
                    '.get_records_to_load_into_xis',
                    return_value=None) as mock_check_records_to_load:
            xiaConfig = XIAConfiguration(publisher='AGENT')
            xiaCfg.first.return_value = xiaConfig
            response_obj.return_value = response_obj
            response_obj.status_code = 201

            meta_obj.return_value = meta_obj
            meta_obj.exclude.return_value = meta_obj
            meta_obj.update.return_value = meta_obj
            meta_obj.filter.side_effect = [meta_obj, meta_obj, meta_obj,
                                           meta_obj]

            post_data_to_xis(data)
            self.assertEqual(response_obj.call_count, 0)
            self.assertEqual(mock_check_records_to_load.call_count, 1)

    def test_post_data_to_xis_more_than_one(self):
        """Test for POSTing XIA metadata_ledger to XIS metadata_ledger
        when more than one rows are passing"""
        data = [self.xia_data,
                self.xia_data]
        with patch(
                'openlxp_xia.management.commands.load_target_metadata'
                '.rename_metadata_ledger_fields',
                return_value=self.xis_expected_data), \
                patch('openlxp_xia.management.utils.xia_internal'
                      '.get_publisher_detail'), \
                patch('openlxp_xia.management.utils.xia_internal'
                      '.XIAConfiguration.objects') as xiaCfg, \
                patch('openlxp_xia.management.commands.load_target_metadata.'
                      'MetadataLedger.objects') as meta_obj, \
                patch('requests.post') as response_obj, \
                patch('openlxp_xia.management.utils.xis_client.'
                      'XISConfiguration.objects') as xisCfg, \
                patch('openlxp_xia.management.commands.load_target_metadata.'
                      'get_records_to_load_into_xis',
                      return_value=None) as mock_check_records_to_load:
            xiaConfig = XIAConfiguration(publisher='AGENT')
            xiaCfg.first.return_value = xiaConfig
            xisConfig = XISConfiguration(
                xis_metadata_api_endpoint=self.xis_api_endpoint_url)
            xisCfg.first.return_value = xisConfig
            response_obj.return_value = response_obj
            response_obj.status_code = 201

            meta_obj.return_value = meta_obj
            meta_obj.exclude.return_value = meta_obj
            meta_obj.update.return_value = meta_obj
            meta_obj.filter.side_effect = [meta_obj, meta_obj, meta_obj,
                                           meta_obj]

            post_data_to_xis(data)
            self.assertEqual(response_obj.call_count, 2)
            self.assertEqual(mock_check_records_to_load.call_count, 1)

        # Test cases for load_supplemental_metadata

    def test_rename_supplemental_metadata_fields(self):
        """Test for Renaming XIA column names to match with XIS column names"""
        with patch('openlxp_xia.management.utils.xia_internal'
                   '.get_publisher_detail'), \
                patch('openlxp_xia.management.utils.xia_internal'
                      '.XIAConfiguration.objects') as xisCfg:
            xiaConfig = XIAConfiguration(publisher='AGENT')
            xisCfg.first.return_value = xiaConfig
            return_data = rename_supplemental_metadata_fields(
                self.xia_supplemental_data)
            self.assertEquals(
                self.xis_supplemental_expected_data['metadata_hash'],
                return_data['metadata_hash'])
            self.assertEquals(
                self.xis_supplemental_expected_data['metadata_key'],
                return_data['metadata_key'])
            self.assertEquals(
                self.xis_supplemental_expected_data['metadata_key_hash'],
                return_data['metadata_key_hash'])
            self.assertEquals(
                self.xis_supplemental_expected_data['provider_name'],
                return_data['provider_name'])

    def test_load_supplemental_metadata_to_xis_one_record(self):
        """Test to Retrieve number of Metadata_Ledger records in XIA to load
        into XIS  and calls the post_data_to_xis accordingly"""
        with patch(
                'openlxp_xia.management.commands.'
                'load_supplemental_metadata'
                '.post_supplemental_metadata_to_xis', return_value=None)as \
                mock_post_data_to_xis, \
                patch(
                    'openlxp_xia.management.commands.'
                    'load_supplemental_metadata'
                    '.SupplementalLedger.objects') as meta_obj:
            meta_data = SupplementalLedger(
                record_lifecycle_status='Active',
                supplemental_metadata=self.supplemental_data,
                supplemental_metadata_hash=self.target_hash_value,
                supplemental_metadata_key_hash=self.target_key_value_hash,
                supplemental_metadata_key=self.target_key_value,
                supplemental_metadata_transmission_date=timezone.now(),
                supplemental_metadata_transmission_status='Ready')
            meta_obj.return_value = meta_obj
            meta_obj.exclude.return_value = meta_obj
            meta_obj.values.return_value = [meta_data]
            meta_obj.filter.side_effect = [meta_obj, meta_obj]
            load_supplemental_metadata_to_xis()
            self.assertEqual(
                mock_post_data_to_xis.call_count, 1)

    def test_load_supplemental_metadata_to_xis_zero(self):
        """Test to Retrieve number of Metadata_Ledger records in XIA to load
        into XIS  and calls the post_data_to_xis accordingly"""
        with patch(
                'openlxp_xia.management.commands.'
                'load_supplemental_metadata'
                '.post_supplemental_metadata_to_xis', return_value=None)as \
                mock_post_data_to_xis, \
                patch('openlxp_xia.management.commands.'
                      'load_supplemental_metadata.'
                      'SupplementalLedger.objects') as meta_obj:
            meta_obj.return_value = meta_obj
            meta_obj.exclude.return_value = meta_obj
            meta_obj.filter.side_effect = [meta_obj, meta_obj]
            load_supplemental_metadata_to_xis()
            self.assertEqual(
                mock_post_data_to_xis.call_count, 0)

    def test_post_supplemental_metadata_to_xis_zero(self):
        """Test for POSTing XIA metadata_ledger to XIS metadata_ledger
        when data is not present"""
        data = []
        with patch(
                'openlxp_xia.management.commands.'
                'load_supplemental_metadata'
                '.rename_supplemental_metadata_fields',
                return_value=self.xis_expected_data), \
                patch('openlxp_xia.management.utils.xia_internal'
                      '.get_publisher_detail'), \
                patch('openlxp_xia.management.utils.xia_internal'
                      '.XIAConfiguration.objects') as xiaCfg, \
                patch(
                    'openlxp_xia.management.commands.'
                    'load_supplemental_metadata'
                    '.SupplementalLedger.objects') as meta_obj, \
                patch('requests.post') as response_obj, \
                patch('openlxp_xia.management.commands.'
                      'load_supplemental_metadata.'
                      'load_supplemental_metadata_to_xis',
                      return_value=None) as mock_check_records_to_load:
            xiaConfig = XIAConfiguration(publisher='AGENT')
            xiaCfg.first.return_value = xiaConfig
            response_obj.return_value = response_obj
            response_obj.status_code = 201

            meta_obj.return_value = meta_obj
            meta_obj.exclude.return_value = meta_obj
            meta_obj.update.return_value = meta_obj
            meta_obj.filter.side_effect = [meta_obj, meta_obj, meta_obj,
                                           meta_obj]

            post_supplemental_metadata_to_xis(data)
            self.assertEqual(response_obj.call_count, 0)
            self.assertEqual(mock_check_records_to_load.call_count, 1)

    def test_post_supplemental_metadata_to_xis_more_than_one(self):
        """Test for POSTing XIA metadata_ledger to XIS metadata_ledger
        when more than one rows are passing"""
        data = [self.xia_supplemental_data,
                self.xia_supplemental_data]
        with patch(
                'openlxp_xia.management.commands.'
                'load_supplemental_metadata'
                '.rename_supplemental_metadata_fields',
                return_value=self.xis_expected_data), \
                patch('openlxp_xia.management.utils.xia_internal'
                      '.get_publisher_detail'), \
                patch('openlxp_xia.management.utils.xia_internal'
                      '.XIAConfiguration.objects') as xiaCfg, \
                patch(
                    'openlxp_xia.management.commands.'
                    'load_supplemental_metadata'
                    '.SupplementalLedger.objects') as meta_obj, \
                patch('requests.post') as response_obj, \
                patch('openlxp_xia.management.utils.xis_client'
                      '.XISConfiguration.objects') as xisCfg, \
                patch(
                    'openlxp_xia.management.commands.'
                    'load_supplemental_metadata'
                    '.load_supplemental_metadata_to_xis',
                    return_value=None) as mock_check_records_to_load:
            xiaConfig = XIAConfiguration(publisher='AGENT')
            xiaCfg.first.return_value = xiaConfig
            xisConfig = \
                XISConfiguration(xis_metadata_api_endpoint=self.
                                 supplemental_api_endpoint)
            xisCfg.first.return_value = xisConfig
            response_obj.return_value = response_obj
            response_obj.status_code = 201

            meta_obj.return_value = meta_obj
            meta_obj.exclude.return_value = meta_obj
            meta_obj.update.return_value = meta_obj
            meta_obj.filter.side_effect = [meta_obj, meta_obj, meta_obj,
                                           meta_obj]

            post_supplemental_metadata_to_xis(data)
            self.assertEqual(response_obj.call_count, 2)
            self.assertEqual(mock_check_records_to_load.call_count, 1)
