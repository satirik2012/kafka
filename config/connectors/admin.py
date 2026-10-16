from django.contrib import admin
from django.utils.html import format_html

from .models import ConnectorConfig, System


@admin.register(System)
class SystemAdmin(admin.ModelAdmin):
    list_display = ('name', 'usage_badge', 'code', 'order')
    list_filter = ('usage',)
    search_fields = ('name', 'code')
    list_editable = ('order',)
    list_display_links = ('name',)
    ordering = ('order', 'name')

    @admin.display(description='Назначение')
    def usage_badge(self, obj):
        color = '#1a7f64' if obj.usage == System.SOURCE else '#b45309'
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 9px;'
            'border-radius:12px;font-size:12px">{}</span>',
            color, obj.get_usage_display())


@admin.register(ConnectorConfig)
class ConnectorConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'usage_badge', 'connector_type',
                    'created_at', 'updated_at')
    list_filter = ('direction', 'connector_type')
    search_fields = ('name', 'connector_class')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    @admin.display(description='Формат')
    def usage_badge(self, obj):
        color = '#1a7f64' if obj.direction == ConnectorConfig.SOURCE else '#b45309'
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 9px;'
            'border-radius:12px;font-size:12px">{}</span>',
            color, obj.get_direction_display())