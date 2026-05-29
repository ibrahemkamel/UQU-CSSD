from django.contrib import admin
from .models import (
    Location,
    CSSDTemplate,
    CSSDTemplateItem,
    CSSDRequest,
    CSSDRequestTemplate,
    CSSDRequestItem,
    Notification,
)


class CSSDRequestTemplateInline(admin.TabularInline):
    model = CSSDRequestTemplate
    extra = 1


@admin.register(CSSDRequest)
class CSSDRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'location', 'procedure', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'location')
    search_fields = ('procedure',)
    inlines = [CSSDRequestTemplateInline]
    readonly_fields = ('status', 'created_by', 'created_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
            obj.status = 'SENT_TO_CSSD'
        super().save_model(request, obj, form, change)


admin.site.register(Location)
admin.site.register(CSSDTemplate)
admin.site.register(CSSDTemplateItem)
admin.site.register(CSSDRequestItem)
admin.site.register(Notification)