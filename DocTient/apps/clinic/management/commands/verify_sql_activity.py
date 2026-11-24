from django.core.management.base import BaseCommand
from django.db.models import Subquery

from apps.clinic.models import PatientProfile, VitalSign


class Command(BaseCommand):
    help = "Verify and print the Django ORM generated SQL for the JOIN and SUBQUERY activity."

    def handle(self, *args, **options):
        vitals = VitalSign.objects.select_related("patient").all()
        vital_patient_ids = VitalSign.objects.values("patient_id")
        patients = PatientProfile.objects.filter(
            id__in=Subquery(vital_patient_ids)
        ).order_by("id")

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== PART 1: SQL JOIN (select_related) ==="))
        self.stdout.write("ORM: VitalSign.objects.select_related('patient').all()\n")
        self.stdout.write(f"Generated SQL:\n{vitals.query}\n")
        self.stdout.write(f"Matched Rows: {vitals.count()}")
        for v in vitals[:5]:
            self.stdout.write(
                f"  - Vital #{v.id} | Patient: {v.patient.full_name} | "
                f"BP: {v.systolic}/{v.diastolic} | HR: {v.heart_rate} | Status: {v.monitoring_status}"
            )

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== PART 2: SQL SUBQUERY (Subquery) ==="))
        self.stdout.write(
            "ORM: PatientProfile.objects.filter(id__in=Subquery(VitalSign.objects.values('patient_id')))\n"
        )
        self.stdout.write(f"Generated SQL:\n{patients.query}\n")
        self.stdout.write(
            f"Matched Patients: {patients.count()} / {PatientProfile.objects.count()} total"
        )
        for p in patients:
            self.stdout.write(
                f"  - Patient #{p.id} | {p.full_name} | Gender: {p.gender} | Contact: {p.contact_no}"
            )
