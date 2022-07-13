import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from openlxp_xia.management.utils.xss_client import (
    get_data_types_for_validation, get_required_fields_for_validation,
    read_json_data)
from openlxp_xia.models import MetadataFieldOverwrite, XIAConfiguration

logger = logging.getLogger('dict_config_logger')


@receiver(post_save, sender=XIAConfiguration)
def save_XIAConfiguration(sender, instance, created, **kwargs):
    """Retrieve list of field required to be overwritten"""

    # Deleting the corresponding existing value to overwrite
    MetadataFieldOverwrite.objects.all().delete()

    datatype_to_str = {
        int: "int",
        str: "str",
        bool: "bool"
    }
    schema_data_dict = read_json_data(instance.target_metadata_schema)
    required_list, recommended_list = \
        get_required_fields_for_validation(schema_data_dict)

    data_type_dict = get_data_types_for_validation(schema_data_dict)

    for element in required_list:
        metadata_field_overwrite = MetadataFieldOverwrite()
        metadata_field_overwrite.field_name = element
        if element in data_type_dict:
            if data_type_dict[element] in datatype_to_str:
                data_type_dict[element] = \
                    datatype_to_str[data_type_dict[element]]
            metadata_field_overwrite.field_type = data_type_dict[element]
        else:
            metadata_field_overwrite.field_type = "str"
            logger.warning("Datatype for required value " +
                           element +
                           " not found in schema mapping")
        metadata_field_overwrite.save()
