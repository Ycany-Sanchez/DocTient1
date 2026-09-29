from django.contrib import admin
from .models import (
    PatientProfile,
    DoctorProfile,
    VitalSign,
    Message,
    Medication,
    MedicationLog,
    DoctorNote,
    DoctorPatientConnection,
)

admin.site.register(PatientProfile)
admin.site.register(DoctorProfile)
admin.site.register(VitalSign)
admin.site.register(Message)
admin.site.register(Medication)
admin.site.register(MedicationLog)
admin.site.register(DoctorNote)
admin.site.register(DoctorPatientConnection)
