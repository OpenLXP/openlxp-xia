from django.contrib import admin

from .models import MetadataFieldOverwrite, XIAConfiguration, XISConfiguration


@admin.register(XIAConfiguration)
class XIAConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        'publisher',
        'source_metadata_schema',
        'source_target_mapping',
        'target_metadata_schema',)
    fields = ['publisher',
              'source_metadata_schema',
              ('source_target_mapping',
               'target_metadata_schema')]

    def delete_queryset(self, request, queryset):
        metadata_fields = MetadataFieldOverwrite.objects.all()
        metadata_fields.delete()
        super().delete_queryset(request, queryset)


@admin.register(XISConfiguration)
class XISConfigurationAdmin(admin.ModelAdmin):
    list_display = ('xis_metadata_api_endpoint',
                    'xis_supplemental_api_endpoint',)
    fields = ['xis_metadata_api_endpoint',
              'xis_supplemental_api_endpoint']


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
