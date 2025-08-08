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

from openlxp_xia.models import (XISConfiguration,
                                supplementalTransmissionStatus as meta_status)

logger = logging.getLogger('dict_config_logger')


def rename_supplemental_metadata_fields(xis, data):
    """Renaming XIA column names to match with XIS column names"""
    data['unique_record_identifier'] = data.pop('metadata_record_uuid')
    data['metadata'] = data.pop('supplemental_metadata')
    data['metadata_hash'] = data.pop('supplemental_metadata_hash')
    data['metadata_key'] = data.pop('supplemental_metadata_key')
    data['metadata_key_hash'] = data.pop('supplemental_metadata_key_hash')
    # Adding Publisher in the list to POST to XIS
    data['provider_name'] = get_publisher_detail(xis)
    return data


def post_supplemental_metadata_to_xis(xis, data):
    """POSTing XIA metadata_ledger to XIS metadata_ledger"""
    # Traversing through each row one by one from data
    # get_xis_supplemental_metadata_api_endpoint
    for row in data:
        data = rename_supplemental_metadata_fields(xis, row)
        renamed_data = json.dumps(data, cls=DjangoJSONEncoder)

        # Getting UUID to update target_metadata_transmission_status to pending
        uuid_val = data.get('unique_record_identifier')

        metadata_record = SupplementalLedger.objects.filter(
            metadata_record_uuid=uuid_val).first()

        if metadata_record:

            trans_status = meta_status.objects.filter(
                metadata_record=metadata_record,
                XISConfiguration=xis
            ).first()

            trans_status.supplemental_metadata_transmission_status = 'Pending'

        # POSTing data to XIS
            try:
                xis_response = \
                    posting_supplemental_metadata_to_xis(xis,
                                                         renamed_data)

                # Receiving XIS response after validation and updating
                # metadata_ledger
                if xis_response.status_code == 201:
                    trans_status.target_metadata_transmission_status = \
                        'Successful'
                    trans_status.target_metadata_transmission_date = \
                        timezone.now()
                    trans_status.target_metadata_transmission_status_code = \
                        xis_response.status_code
                    logger.info(
                        "Data " + str(metadata_record) +
                        "successfully posted to XIS with status code "
                        + str(xis_response.status_code))
                else:
                    trans_status.target_metadata_transmission_status = 'Failed'
                    trans_status.target_metadata_transmission_date = \
                        timezone.now()
                    trans_status.target_metadata_transmission_status_code = \
                        xis_response.status_code
                    logger.warning(
                        "Bad request sent " + str(xis_response.status_code)
                        + "error found " + xis_response.text)
                trans_status.save()
            except requests.exceptions.RequestException as e:
                logger.error(e)
                # Updating status in XIA metadata_ledger to 'Failed'
                trans_status.target_metadata_transmission_status = 'Failed'
                trans_status.save()
                raise SystemExit('Exiting! Can not make connection with XIS.')

    load_supplemental_metadata_to_xis(xis)


def load_supplemental_metadata_to_xis(xis):
    """Retrieve number of Metadata_Ledger records in XIA to load into XIS  and
    calls the post_data_to_xis accordingly"""

    records = SupplementalLedger.objects.filter(
        record_lifecycle_status='Active').\
        exclude(supplemental_metadata_validation_date__isnull=True)

    if xis:
        for record in records:
            meta_status.objects.get_or_create(
                metadata_record=record,
                XISConfiguration=xis,
                defaults={'target_metadata_transmission_status': 'Ready'}
            )
        combined_query = meta_status.objects.filter(
            Q(target_metadata_transmission_status='Ready') | Q(
                target_metadata_transmission_status='Failed') | Q(
                target_metadata_transmission_status='Pending') &
            Q(XISConfiguration=xis))

        data = SupplementalLedger.objects.filter(
            meta_status__in=combined_query,
            record_lifecycle_status='Active'
        ).exclude(
            meta_status__target_metadata_transmission_status_code=400
        ).values(
            'metadata_record_uuid',
            'supplemental_metadata',
            'supplemental_metadata_hash',
            'supplemental_metadata_key',
            'supplemental_metadata_key_hash')

        # Checking available no. of records in XIA to load
        # into XIS is Zero or not
        if len(data) == 0:
            logger.info("Supplemental Metadata Loading in XIS is complete, "
                        "Zero records are available in XIA to transmit")
        else:
            post_supplemental_metadata_to_xis(xis, data)


class Command(BaseCommand):
    """Django command to load supplemental metadata in the Experience Index
    Service (XIS)"""

    def add_arguments(self, parser):
        parser.add_argument('--config_id', type=int, help='ID of the config')

    def handle(self, *args, **options):
        """Metadata is load from XIA Supplemental_Ledger to XIS
        Metadata_Ledger"""
        xis = None
        if 'config' in options:
            xis = options['config'].xis_configuration
            logger.info(xis)
        elif 'config_id' in options:
            # If config_id is provided, fetch the XIAConfiguration object
            try:
                xis = XISConfiguration.objects.get(id=options['config_id'])
                logger.info(xis)
            except XISConfiguration.DoesNotExist:
                logger.error(
                    f'XIS Configuration with ID {options["config_id"]}'
                    ' does not exist')
                return
        if not xis:
            # If xis is not provided, log an error and exit
            xis = XISConfiguration.objects.first()
            if not xis:
                logger.error('XIS Configuration is not provided')
                raise SystemExit('XIS Configuration is not provided')
        load_supplemental_metadata_to_xis(xis)
