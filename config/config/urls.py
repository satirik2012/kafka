from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Kafka Connect Survey — панель управления'
admin.site.site_title = 'Kafka Connect Survey'
admin.site.index_title = 'Справочники и конфигурации'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('connectors.urls')),
]