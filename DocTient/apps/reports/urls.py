from django.urls import path
from .views import (
    reports_view,
    patient_vitals_join_view,
    patients_with_vitals_subquery_view,
)

app_name = "reports"

urlpatterns = [
    path("", reports_view, name="reports"),
    path("vitals-join/", patient_vitals_join_view, name="vitals_join"),
    path("patients-subquery/", patients_with_vitals_subquery_view, name="patients_subquery"),
]


