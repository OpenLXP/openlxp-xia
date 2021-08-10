import logging

from django.core.management.base import BaseCommand

from openlxp_xia.management.utils.notification import send_notifications
from openlxp_xia.models import (ReceiverEmailConfiguration,
                                SenderEmailConfiguration)

logger = logging.getLogger('dict_config_logger')


def send_log_email():
    """ function to send emails of log file to personas"""

    # getting email id to send email to personas

    email_data = ReceiverEmailConfiguration.objects.values_list(
        'email_address',
        flat=True)
    email = list(email_data)
    # Getting sender email id
    sender_email_configuration = SenderEmailConfiguration.objects.first()
    sender = sender_email_configuration.sender_email_address
    send_notifications(email, sender)


class Command(BaseCommand):
    """Django command to send an emails to the filer/personas, when the log
    warning/error occurred in the metadata EVTVL process."""

    def handle(self, *args, **options):
        """Email log notification is sent to filer/personas when warning/error
        occurred in EVTVL process"""
        send_log_email()
