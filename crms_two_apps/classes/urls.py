from django.urls import path

from . import views

app_name = "classes"

urlpatterns = [
    path(
        "",
        views.class_list,
        name="list",
    ),
    path(
        "create/",
        views.class_create,
        name="create",
    ),
    path(
        "<int:class_id>/",
        views.class_detail,
        name="detail",
    ),
    path(
        "<int:class_id>/students/json/",
        views.class_students_json,
        name="students_json",
    ),
    path(
        "<int:class_id>/enroll/",
        views.enroll_student,
        name="enroll",
    ),
]
