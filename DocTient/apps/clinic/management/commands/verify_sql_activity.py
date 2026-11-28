from django.core.management.base import BaseCommand
from django.db import connection

from apps.clinic.models import DoctorProfile, PatientProfile


class Command(BaseCommand):
    help = "Print and run the SQL JOIN and SUBQUERY queries against Supabase."

    def handle(self, *args, **options):
        # PART 1: SQL JOIN (matching apps/home/views.py — Doctor Dashboard Patient Directory)
        join_sql = (
            "SELECT p.full_name, a.username, p.date_of_birth, p.gender, a.email\n"
            "FROM patient_profiles p\n"
            "INNER JOIN auth_user a ON (p.user_id = a.id)\n"
            "ORDER BY p.full_name ASC;"
        )
        with connection.cursor() as cursor:
            cursor.execute(join_sql)
            join_rows = cursor.fetchall()

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== PART 1: SQL JOIN (apps/home/views.py — Doctor Dashboard) ==="))
        self.stdout.write(f"SQL Query:\n{join_sql}\n")
        self.stdout.write(f"Matched Rows: {len(join_rows)}")
        for full_name, username, dob, gender, email in join_rows:
            self.stdout.write(
                f"  - {full_name} | @{username} | DOB: {dob or '-'} | "
                f"Gender: {gender or '-'} | Email: {email or '-'}"
            )

        # PART 2: SQL SUBQUERY (matching apps/reports/views.py — Doctor Cohort Report)
        doctor = (
            DoctorProfile.objects.filter(user__username="dr_santos").first()
            or DoctorProfile.objects.first()
        )
        subquery_sql = (
            "SELECT p.full_name, p.date_of_birth, p.gender, p.contact_no, p.address\n"
            "FROM patient_profiles p\n"
            "WHERE p.id IN (\n"
            "    SELECT c.patient_id\n"
            "    FROM doctor_patient_connections c\n"
            "    WHERE c.doctor_id = %s\n"
            ")\n"
            "ORDER BY p.full_name ASC;"
        )
        with connection.cursor() as cursor:
            cursor.execute(subquery_sql, [doctor.id])
            subquery_rows = cursor.fetchall()

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== PART 2: SQL SUBQUERY (apps/reports/views.py — Doctor Reports for Dr. {doctor.full_name}) ==="
        ))
        self.stdout.write(f"SQL Query:\n{subquery_sql % doctor.id}\n")
        self.stdout.write(
            f"Matched Cohort Patients: {len(subquery_rows)} / {PatientProfile.objects.count()} total patients"
        )
        for full_name, dob, gender, contact_no, address in subquery_rows:
            self.stdout.write(
                f"  - {full_name} | DOB: {dob or '-'} | Gender: {gender or '-'} | "
                f"Contact: {contact_no or '-'} | Address: {address or '-'}"
            )
