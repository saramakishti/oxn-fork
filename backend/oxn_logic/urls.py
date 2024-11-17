from django.urls import path
from . import views

urlpatterns = [
    path('api/helloworld', views.hello_world, name='hello_world'), 
]