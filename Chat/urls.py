# urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('chat_with_documents', views.chat_with_documents, name='chat_with_documents'),
    path('choose_bot', views.choose_bot, name='choose_bot'),
    path('login', views.login, name='login'),
    path('register', views.register, name='register'),
]
