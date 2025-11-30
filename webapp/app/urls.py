from django.urls import path
from . import views

urlpatterns = [
    path("login", views.login_form),
    path("feature", views.feature_form)
    
]