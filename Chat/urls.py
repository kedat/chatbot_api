# urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('chat_with_documents', views.chat_with_documents, name='chat_with_documents'),
    path('update_data', views.update_data, name='update_data'),
    path('login', views.login, name='login'),
    path('register', views.register, name='register'),
]
