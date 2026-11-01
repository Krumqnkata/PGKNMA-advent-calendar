from django.urls import path

from . import views

app_name = "doors"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/doors/", views.door_list, name="door-list"),
    path("api/doors/<int:day>/", views.door_detail, name="door-detail"),
    path("api/doors/<int:day>/react/", views.door_react, name="door-react"),
    path("api/visit/", views.visit, name="visit"),
]
