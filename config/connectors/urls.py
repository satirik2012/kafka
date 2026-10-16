from django.urls import path

from . import views

app_name = 'connectors'

urlpatterns = [
    path('', views.welcome, name='welcome'),
    path('system/', views.system_step, name='system'),
    path('summary/', views.summary, name='summary'),
    path('settings/', views.settings_page, name='settings'),
    path('transforms/', views.transforms_admin, name='transforms'),
]