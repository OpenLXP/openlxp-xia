import json
import logging

import requests
from django.core.management.base import BaseCommand
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.utils import timezone

from openlxp_xia.management.utils.xia_internal import get_publisher_detail
from openlxp_xia.management.utils.xis_client import \
    posting_metadata_ledger_to_xis
from openlxp_xia.models import MetadataLedger

logger = logging.getLogger('dict_config_logger')


def rename_metadata_ledger_fields(data):
    """Renaming XIA column names to match with XIS column names"""
    data['unique_record_identifier'] = data.pop('metadata_record_uuid')
    data['metadata'] = data.pop('target_metadata')
    data['metadata_hash'] = data.pop('target_metadata_hash')
    data['metadata_key'] = data.pop('target_metadata_key')
    data['metadata_key_hash'] = data.pop('target_metadata_key_hash')
    # Adding Publisher in the list to POST to XIS
    data['provider_name'] = get_publisher_detail()
    return data


def post_data_to_xis(data):
    """POSTing XIA metadata_ledger to XIS metadata_ledger"""
    # Traversing through each row one by one from data
    for row in data:
        data = rename_metadata_ledger_fields(row)
        renamed_data = json.dumps(data, cls=DjangoJSONEncoder)

        # Getting UUID to update target_metadata_transmission_status to pending
        uuid_val = data.get('unique_record_identifier')

        # Updating status in XIA metadata_ledger to 'Pending'
        MetadataLedger.objects.filter(
            metadata_record_uuid=uuid_val).update(
            target_metadata_transmission_status='Pending')

        # POSTing data to XIS
        try:
            xis_response = posting_metadata_ledger_to_xis(renamed_data)

            # Receiving XIS response after validation and updating
            # metadata_ledger
            if xis_response.status_code == 201:
                MetadataLedger.objects.filter(
                    metadata_record_uuid=uuid_val).update(
                    target_metadata_transmission_status_code=xis_response.
                        status_code,
                    target_metadata_transmission_status='Successful',
                    target_metadata_transmission_date=timezone.now())
            else:
                MetadataLedger.objects.filter(
                    metadata_record_uuid=uuid_val).update(
                    target_metadata_transmission_status_code=xis_response.
                        status_code,
                    target_metadata_transmission_status='Failed',
                    target_metadata_transmission_date=timezone.now())
                logger.warning(
                    "Bad request sent " + str(xis_response.status_code)
                    + "error found " + xis_response.text)
        except requests.exceptions.RequestException as e:
            logger.error(e)
            # Updating status in XIA metadata_ledger to 'Failed'
            MetadataLedger.objects.filter(
                metadata_record_uuid=uuid_val).update(
                target_metadata_transmission_status='Failed')
            raise SystemExit('Exiting! Can not make connection with XIS.')

    get_records_to_load_into_xis()


def get_records_to_load_into_xis():
    """Retrieve number of Metadata_Ledger records in XIA to load into XIS  and
    calls the post_data_to_xis accordingly"""
    combined_query = MetadataLedger.objects.filter(
        Q(target_metadata_transmission_status='Ready') | Q(
            target_metadata_transmission_status='Failed'))

    data = combined_query.filter(
        record_lifecycle_status='Active',
        target_metadata_validation_status='Y').exclude(
        target_metadata_transmission_status_code=400).values(
        'metadata_record_uuid',
        'target_metadata',
        'target_metadata_hash',
        'target_metadata_key',
        'target_metadata_key_hash')

    # Checking available no. of records in XIA to load into XIS is Zero or not
    if len(data) == 0:
        logger.info("Data Loading in XIS is complete, Zero records are "
                    "available in XIA to transmit")
    else:
        post_data_to_xis(data)


class Command(BaseCommand):
    """Django command to load metadata in the Experience Index Service (XIS)"""

    def handle(self, *args, **options):
        """Metadata is load from XIA Metadata_Ledger to XIS Metadata_Ledger"""
        get_records_to_load_into_xis()
