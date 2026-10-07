from django.urls import path

from .views import messages_view

app_name = "messages"

urlpatterns = [
    path("", messages_view, name="messages"),
]
