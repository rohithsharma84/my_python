from django.urls import path
from . import views

app_name = 'bank'

urlpatterns = [
    path('', views.account_setup, name='account_setup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/action/', views.account_action, name='account_action'),
]
