from django.contrib import admin

from .models import MetadataFieldOverwrite, XIAConfiguration, XISConfiguration


def marked_default(MetadataFieldOverwriteAdmin, request, queryset):
    queryset.filter(field_type="str").update(field_value='Not Available')
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
    actions = [marked_default, unmarked_default]
