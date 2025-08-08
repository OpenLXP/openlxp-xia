from django.contrib import admin

from .models import (MetadataFieldOverwrite, SupplementalLedger,
                     XIAConfiguration,
                     XISConfiguration, MetadataLedger)


def marked_default(MetadataFieldOverwriteAdmin, request, queryset):
    queryset.filter(field_type="str").update(field_value='Not Available')
    queryset.filter(field_type="URI").update(field_value='Not Available')
    queryset.filter(field_type="datetime").\
        update(field_value='1900-01-01T00:00:00-05:00')
    queryset.filter(field_type="INT").update(field_value=0)
    queryset.filter(field_type="BOOL").update(field_value=False)


def unmarked_default(MetadataFieldOverwriteAdmin, request, queryset):
    queryset.update(field_value=None)


marked_default.short_description = "Mark default values for fields"
unmarked_default.short_description = "Unmarked default values for fields"


@admin.register(XIAConfiguration)
class XIAConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        'publisher', 'xss_api',
        'source_metadata_schema',
        'target_metadata_schema',)
    fields = ['publisher', 'xss_api',
              ('source_metadata_schema',
               'target_metadata_schema'),
              'key_fields']

    def delete_queryset(self, request, queryset):
        metadata_fields = MetadataFieldOverwrite.objects.all()
        metadata_fields.delete()
        super().delete_queryset(request, queryset)


@admin.register(XISConfiguration)
class XISConfigurationAdmin(admin.ModelAdmin):
    list_display = ('publisher',
                    'xis_metadata_api_endpoint',
                    'xis_supplemental_api_endpoint',)
    fields = ['publisher',
              'xis_metadata_api_endpoint',
              'xis_supplemental_api_endpoint', 'xis_api_key']


@admin.register(MetadataFieldOverwrite)
class MetadataFieldOverwriteAdmin(admin.ModelAdmin):
    list_display = ('field_name',
                    'field_type',
                    'field_value',
                    'overwrite',)
    fields = ['field_name',
              'field_type',
              'field_value',
              'overwrite']
    actions = [marked_default, unmarked_default]


@admin.register(MetadataLedger)
class MetadataLedgerAdmin(admin.ModelAdmin):
    list_display = ('metadata_record_uuid',
                    'source_metadata_key',
                    'source_metadata_validation_status',
                    'target_metadata_validation_status',
                    'record_lifecycle_status',)

    list_filter = ('record_lifecycle_status',
                   'target_metadata_validation_status')
    search_fields = ('metadata_record_uuid',
                     'source_metadata_key',)


@admin.register(SupplementalLedger)
class SupplementalLedgerAdmin(admin.ModelAdmin):
    list_display = ('metadata_record_uuid',
                    'supplemental_metadata_key',
                    'record_lifecycle_status',)

    list_filter = ('record_lifecycle_status',)
    search_fields = ('supplemental_metadata_key',)
