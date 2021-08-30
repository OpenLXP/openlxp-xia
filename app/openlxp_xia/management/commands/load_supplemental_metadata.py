import json
import logging

import requests
from django.core.management.base import BaseCommand
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.utils import timezone

from openlxp_xia.management.utils.xia_internal import get_publisher_detail
from openlxp_xia.management.utils.xis_client import \
    posting_supplemental_metadata_to_xis
from openlxp_xia.models import SupplementalLedger

logger = logging.getLogger('dict_config_logger')


def rename_supplemental_metadata_fields(data):
    """Renaming XIA column names to match with XIS column names"""
    data['unique_record_identifier'] = data.pop('metadata_record_uuid')
    data['metadata'] = data.pop('supplemental_metadata')
    data['metadata_hash'] = data.pop('supplemental_metadata_hash')
    data['metadata_key'] = data.pop('supplemental_metadata_key')
    data['metadata_key_hash'] = data.pop('supplemental_metadata_key_hash')
    # Adding Publisher in the list to POST to XIS
    data['provider_name'] = get_publisher_detail()
    return data


def post_supplemental_metadata_to_xis(data):
    """POSTing XIA metadata_ledger to XIS metadata_ledger"""
    # Traversing through each row one by one from data
    # get_xis_supplemental_metadata_api_endpoint
    for row in data:
        data = rename_supplemental_metadata_fields(row)
        renamed_data = json.dumps(data, cls=DjangoJSONEncoder)

        # Getting UUID to update target_metadata_transmission_status to pending
        uuid_val = data.get('unique_record_identifier')

        # Updating status in XIA metadata_ledger to 'Pending'
        SupplementalLedger.objects.filter(
            metadata_record_uuid=uuid_val).update(
            supplemental_metadata_transmission_status='Pending')

        # POSTing data to XIS
        try:
            xis_response = posting_supplemental_metadata_to_xis(
                renamed_data)

            # Receiving XIS response after validation and updating
            # metadata_ledger
            if xis_response.status_code == 201:
                SupplementalLedger.objects.filter(
                    metadata_record_uuid=uuid_val).update(
                    supplemental_metadata_transmission_status_code=xis_response
                    .status_code,
                    supplemental_metadata_transmission_status='Successful',
                    supplemental_metadata_transmission_date=timezone.now())
            else:
                SupplementalLedger.objects.filter(
                    metadata_record_uuid=uuid_val).update(
                    supplemental_metadata_transmission_status_code=xis_response
                    .status_code,
                    supplemental_metadata_transmission_status='Failed',
                    supplemental_metadata_transmission_date=timezone.now())
                logger.warning(
                    "Bad request sent " + str(xis_response.status_code)
                    + "error found " + xis_response.text)
        except requests.exceptions.RequestException as e:
            logger.error(e)
            # Updating status in XIA metadata_ledger to 'Failed'
            SupplementalLedger.objects.filter(
                metadata_record_uuid=uuid_val).update(
                supplemental_metadata_transmission_status='Failed')
            raise SystemExit('Exiting! Can not make connection with XIS.')

    load_supplemental_metadata_to_xis()


def load_supplemental_metadata_to_xis():
    """Retrieve number of Metadata_Ledger records in XIA to load into XIS  and
    calls the post_data_to_xis accordingly"""
    combined_query = SupplementalLedger.objects.filter(
        Q(supplemental_metadata_transmission_status='Ready') | Q(
            supplemental_metadata_transmission_status='Failed'))

    data = combined_query.filter(
        record_lifecycle_status='Active').exclude(
        supplemental_metadata_transmission_status_code=400).values(
        'metadata_record_uuid',
        'supplemental_metadata',
        'supplemental_metadata_hash',
        'supplemental_metadata_key',
        'supplemental_metadata_key_hash')

    # Checking available no. of records in XIA to load into XIS is Zero or not
    if len(data) == 0:
        logger.info("Supplemental Metadata Loading in XIS is complete, "
                    "Zero records are available in XIA to transmit")
    else:
        post_supplemental_metadata_to_xis(data)


class Command(BaseCommand):
    """Django command to load supplemental metadata in the Experience Index
    Service (XIS)"""

    def handle(self, *args, **options):
        """Metadata is load from XIA Supplemental_Ledger to XIS
        Metadata_Ledger"""
        load_supplemental_metadata_to_xis()
