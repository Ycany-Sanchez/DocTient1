from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.clinic.models import (
    DoctorNote,
    DoctorPatientConnection,
    DoctorProfile,
    Medication,
    MedicationLog,
    Message,
    PatientProfile,
    VitalSign,
)
from apps.user_profile.models import Profile
from apps.user_settings.models import UserSettings


class Command(BaseCommand):
    help = "Seed clean, realistic clinical data into Supabase for DocTient and SQL JOIN/SUBQUERY demos."

    def handle(self, *args, **options):
        now = timezone.now()

        # 1. Doctors
        ycany_user, _ = User.objects.get_or_create(
            username="Ycany",
            defaults={"email": "ycany.sanchez@doctient.ph"},
        )
        if not ycany_user.email:
            ycany_user.email = "ycany.sanchez@doctient.ph"
            ycany_user.save(update_fields=["email"])

        dr_ycany, _ = DoctorProfile.objects.update_or_create(
            user=ycany_user,
            defaults={
                "full_name": "Ycany Sanchez",
                "med_specialty": "Cardiology & Internal Medicine",
                "contact_no": "0917-555-0101",
                "availability_status": "available",
                "bio": "Attending Cardiologist specializing in remote blood pressure telemetry and preventive care.",
            },
        )
        Profile.objects.update_or_create(
            user=ycany_user,
            defaults={
                "full_name": "Dr. Ycany Sanchez",
                "bio": "Attending Cardiologist · DocTient Clinical Telehealth",
            },
        )
        UserSettings.objects.get_or_create(user=ycany_user)

        dr_santos_user, created = User.objects.get_or_create(
            username="dr_santos",
            defaults={"email": "elena.santos@doctient.ph"},
        )
        if created:
            dr_santos_user.set_password("DocTient123!")
            dr_santos_user.save()
        dr_santos, _ = DoctorProfile.objects.update_or_create(
            user=dr_santos_user,
            defaults={
                "full_name": "Elena Santos",
                "med_specialty": "Pulmonology & Primary Care",
                "contact_no": "0917-555-0102",
                "availability_status": "available",
                "bio": "Primary care and respiratory telemetry specialist.",
            },
        )
        Profile.objects.update_or_create(
            user=dr_santos_user,
            defaults={
                "full_name": "Dr. Elena Santos",
                "bio": "Pulmonology & Primary Care Specialist",
            },
        )
        UserSettings.objects.get_or_create(user=dr_santos_user)

        # 2. Patients (4 with vital signs, 1 newly onboarded without vital signs to showcase SUBQUERY filtering)
        patient_specs = [
            {
                "username": "juan_delacruz",
                "email": "juan.delacruz@email.com",
                "full_name": "Juan Dela Cruz",
                "date_of_birth": date(1985, 4, 12),
                "gender": "Male",
                "height_cm": Decimal("172.00"),
                "weight_kg": Decimal("76.50"),
                "contact_no": "0917-234-5601",
                "address": "Banilad, Cebu City",
                "emergency_contact_no": "0917-900-1101",
            },
            {
                "username": "maria_reyes",
                "email": "maria.reyes@email.com",
                "full_name": "Maria Clara Reyes",
                "date_of_birth": date(1992, 8, 25),
                "gender": "Female",
                "height_cm": Decimal("160.00"),
                "weight_kg": Decimal("56.00"),
                "contact_no": "0917-234-5602",
                "address": "Tipolo, Mandaue City",
                "emergency_contact_no": "0917-900-1102",
            },
            {
                "username": "carlos_mendoza",
                "email": "carlos.mendoza@email.com",
                "full_name": "Carlos Mendoza",
                "date_of_birth": date(1978, 11, 3),
                "gender": "Male",
                "height_cm": Decimal("175.00"),
                "weight_kg": Decimal("84.00"),
                "contact_no": "0917-234-5603",
                "address": "Basak, Lapu-Lapu City",
                "emergency_contact_no": "0917-900-1103",
            },
            {
                "username": "sofia_villanueva",
                "email": "sofia.villanueva@email.com",
                "full_name": "Sofia Villanueva",
                "date_of_birth": date(1995, 2, 19),
                "gender": "Female",
                "height_cm": Decimal("163.00"),
                "weight_kg": Decimal("59.00"),
                "contact_no": "0917-234-5604",
                "address": "Poblacion, Talisay City",
                "emergency_contact_no": "0917-900-1104",
            },
            {
                "username": "miguel_torres",
                "email": "miguel.torres@email.com",
                "full_name": "Miguel Torres",
                "date_of_birth": date(1990, 7, 8),
                "gender": "Male",
                "height_cm": Decimal("170.00"),
                "weight_kg": Decimal("72.00"),
                "contact_no": "0917-234-5605",
                "address": "Lahug, Cebu City",
                "emergency_contact_no": "0917-900-1105",
            },
        ]

        patients = {}
        for spec in patient_specs:
            user, created = User.objects.get_or_create(
                username=spec["username"],
                defaults={"email": spec["email"]},
            )
            if created:
                user.set_password("DocTient123!")
                user.save()
            profile, _ = PatientProfile.objects.update_or_create(
                user=user,
                defaults={
                    "full_name": spec["full_name"],
                    "date_of_birth": spec["date_of_birth"],
                    "gender": spec["gender"],
                    "height_cm": spec["height_cm"],
                    "weight_kg": spec["weight_kg"],
                    "contact_no": spec["contact_no"],
                    "address": spec["address"],
                    "emergency_contact_no": spec["emergency_contact_no"],
                },
            )
            Profile.objects.update_or_create(
                user=user,
                defaults={"full_name": spec["full_name"], "bio": "DocTient Registered Patient"},
            )
            UserSettings.objects.get_or_create(user=user)
            patients[spec["username"]] = profile

        # 3. Vital Signs (only for first 4 patients; Miguel Torres intentionally has 0 vitals)
        if VitalSign.objects.count() == 0:
            VitalSign.objects.bulk_create([
                VitalSign(
                    patient=patients["juan_delacruz"],
                    systolic=148,
                    diastolic=94,
                    heart_rate=86,
                    temperature_celsius=Decimal("36.80"),
                    oxygen_saturation=Decimal("97.50"),
                    weight_kg=Decimal("76.50"),
                    monitoring_status="Stage 2 HTN",
                    patient_notes="Mild morning headache before taking Amlodipine.",
                    recorded_at=now - timedelta(hours=3),
                ),
                VitalSign(
                    patient=patients["juan_delacruz"],
                    systolic=136,
                    diastolic=86,
                    heart_rate=80,
                    temperature_celsius=Decimal("36.60"),
                    oxygen_saturation=Decimal("98.00"),
                    weight_kg=Decimal("76.80"),
                    monitoring_status="Stage 1 HTN",
                    patient_notes="Evening reading after 20-minute walk.",
                    recorded_at=now - timedelta(days=1, hours=4),
                ),
                VitalSign(
                    patient=patients["juan_delacruz"],
                    systolic=128,
                    diastolic=82,
                    heart_rate=76,
                    temperature_celsius=Decimal("36.50"),
                    oxygen_saturation=Decimal("98.50"),
                    weight_kg=Decimal("77.00"),
                    monitoring_status="Stage 1 HTN",
                    patient_notes="Resting reading at home.",
                    recorded_at=now - timedelta(days=3),
                ),
                VitalSign(
                    patient=patients["maria_reyes"],
                    systolic=116,
                    diastolic=74,
                    heart_rate=70,
                    temperature_celsius=Decimal("36.50"),
                    oxygen_saturation=Decimal("99.00"),
                    weight_kg=Decimal("56.00"),
                    monitoring_status="Normal",
                    patient_notes="Feeling energetic, normal fasting reading.",
                    recorded_at=now - timedelta(hours=6),
                ),
                VitalSign(
                    patient=patients["maria_reyes"],
                    systolic=118,
                    diastolic=76,
                    heart_rate=72,
                    temperature_celsius=Decimal("36.60"),
                    oxygen_saturation=Decimal("98.80"),
                    weight_kg=Decimal("56.20"),
                    monitoring_status="Normal",
                    patient_notes="Routine morning check.",
                    recorded_at=now - timedelta(days=2),
                ),
                VitalSign(
                    patient=patients["carlos_mendoza"],
                    systolic=134,
                    diastolic=85,
                    heart_rate=79,
                    temperature_celsius=Decimal("36.70"),
                    oxygen_saturation=Decimal("97.80"),
                    weight_kg=Decimal("84.00"),
                    monitoring_status="Stage 1 HTN",
                    patient_notes="Measured after lunch.",
                    recorded_at=now - timedelta(hours=9),
                ),
                VitalSign(
                    patient=patients["carlos_mendoza"],
                    systolic=126,
                    diastolic=78,
                    heart_rate=75,
                    temperature_celsius=Decimal("36.60"),
                    oxygen_saturation=Decimal("98.20"),
                    weight_kg=Decimal("84.30"),
                    monitoring_status="Elevated",
                    patient_notes="Resting morning vitals.",
                    recorded_at=now - timedelta(days=2, hours=5),
                ),
                VitalSign(
                    patient=patients["sofia_villanueva"],
                    systolic=114,
                    diastolic=72,
                    heart_rate=68,
                    temperature_celsius=Decimal("36.40"),
                    oxygen_saturation=Decimal("99.20"),
                    weight_kg=Decimal("59.00"),
                    monitoring_status="Normal",
                    patient_notes="Baseline wellness check.",
                    recorded_at=now - timedelta(days=1),
                ),
            ])

        # 4. Doctor-Patient Connections
        connections_data = [
            (
                dr_ycany,
                patients["juan_delacruz"],
                "Persistent Stage 2 systolic elevation noted in latest morning telemetry.",
                "Continue Amlodipine 5mg OD, reduce sodium intake, and schedule BP re-check in 48 hours.",
            ),
            (
                dr_ycany,
                patients["maria_reyes"],
                "Hemodynamics stable and within optimal normotensive range.",
                "Maintain current lifestyle regimen and weekly telemetry logging.",
            ),
            (
                dr_ycany,
                patients["carlos_mendoza"],
                "Borderline Stage 1 hypertension improving with statin and diet adjustments.",
                "Log morning and evening BP for the next 7 days.",
            ),
            (
                dr_ycany,
                patients["sofia_villanueva"],
                "Baseline vitals normal with excellent oxygen saturation.",
                "Routine monthly follow-up.",
            ),
            (
                dr_ycany,
                patients["miguel_torres"],
                "Newly onboarded patient awaiting initial home vital signs submission.",
                "Submit baseline blood pressure and heart rate readings via Patient Dashboard.",
            ),
            (
                dr_santos,
                patients["maria_reyes"],
                "Clear respiratory status and SpO2 consistently >= 98%.",
                "Continue preventive wellness checks.",
            ),
            (
                dr_santos,
                patients["sofia_villanueva"],
                "Normal baseline cardiopulmonary screening.",
                "No intervention required.",
            ),
        ]
        for doc, pat, obs, rec in connections_data:
            DoctorPatientConnection.objects.update_or_create(
                doctor=doc,
                patient=pat,
                defaults={"observations": obs, "recommendations": rec},
            )

        # 5. Medications & Medication Logs
        if Medication.objects.count() == 0:
            med_amlodipine = Medication.objects.create(
                patient=patients["juan_delacruz"],
                doctor=dr_ycany,
                medication="Amlodipine",
                dosage="5 mg",
                frequency="Once daily (Morning)",
                scheduled_time=time(8, 0),
                start_date=date.today() - timedelta(days=14),
                status="active",
                reminder_active=True,
            )
            med_losartan = Medication.objects.create(
                patient=patients["juan_delacruz"],
                doctor=dr_ycany,
                medication="Losartan",
                dosage="50 mg",
                frequency="Once daily (Evening)",
                scheduled_time=time(20, 0),
                start_date=date.today() - timedelta(days=10),
                status="active",
                reminder_active=True,
            )
            med_metformin = Medication.objects.create(
                patient=patients["maria_reyes"],
                doctor=dr_santos,
                medication="Metformin",
                dosage="500 mg",
                frequency="Twice daily with meals",
                scheduled_time=time(7, 30),
                start_date=date.today() - timedelta(days=20),
                status="active",
                reminder_active=True,
            )
            med_atorvastatin = Medication.objects.create(
                patient=patients["carlos_mendoza"],
                doctor=dr_ycany,
                medication="Atorvastatin",
                dosage="20 mg",
                frequency="Once daily at bedtime",
                scheduled_time=time(21, 30),
                start_date=date.today() - timedelta(days=15),
                status="active",
                reminder_active=True,
            )

            MedicationLog.objects.bulk_create([
                MedicationLog(
                    medication=med_amlodipine,
                    is_taken=True,
                    taken_at=now - timedelta(hours=4),
                    scheduled_for=now - timedelta(hours=4),
                    remarks="Taken after breakfast",
                ),
                MedicationLog(
                    medication=med_amlodipine,
                    is_taken=True,
                    taken_at=now - timedelta(days=1, hours=4),
                    scheduled_for=now - timedelta(days=1, hours=4),
                    remarks="Taken on schedule",
                ),
                MedicationLog(
                    medication=med_losartan,
                    is_taken=False,
                    taken_at=None,
                    scheduled_for=now - timedelta(days=1),
                    remarks="Missed evening dose",
                ),
                MedicationLog(
                    medication=med_metformin,
                    is_taken=True,
                    taken_at=now - timedelta(hours=5),
                    scheduled_for=now - timedelta(hours=5),
                    remarks="Taken with breakfast",
                ),
                MedicationLog(
                    medication=med_atorvastatin,
                    is_taken=True,
                    taken_at=now - timedelta(hours=14),
                    scheduled_for=now - timedelta(hours=14),
                    remarks="Taken before sleep",
                ),
            ])

        # 6. Doctor Notes
        if DoctorNote.objects.count() == 0:
            DoctorNote.objects.bulk_create([
                DoctorNote(
                    doctor=dr_ycany,
                    observations="Juan Dela Cruz showed elevated morning BP (148/94 mmHg); evening Losartan dose was missed.",
                    recommendations="Reinforce evening medication reminder and review telemetry again tomorrow morning.",
                ),
                DoctorNote(
                    doctor=dr_ycany,
                    observations="Cohort review completed: 4 of 5 connected patients actively logging vitals.",
                    recommendations="Follow up with Miguel Torres to submit initial baseline readings.",
                ),
            ])

        # 7. Messages
        if Message.objects.count() == 0:
            Message.objects.bulk_create([
                Message(
                    sender=patients["juan_delacruz"].user,
                    recipient=ycany_user,
                    content="Good morning Dr. Sanchez, I logged my blood pressure today and it was 148/94.",
                    is_read=True,
                    sent_at=now - timedelta(hours=2, minutes=30),
                ),
                Message(
                    sender=ycany_user,
                    recipient=patients["juan_delacruz"].user,
                    content="Thank you Juan. Please take your Amlodipine on time, rest for 15 minutes, and re-check your BP this afternoon.",
                    is_read=False,
                    sent_at=now - timedelta(hours=2),
                ),
            ])

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded DocTient cleanly: "
                f"{DoctorProfile.objects.count()} doctors, "
                f"{PatientProfile.objects.count()} patients, "
                f"{VitalSign.objects.count()} vital signs, "
                f"{Medication.objects.count()} medications, "
                f"{MedicationLog.objects.count()} medication logs, "
                f"{DoctorPatientConnection.objects.count()} connections, "
                f"{DoctorNote.objects.count()} notes, "
                f"{Message.objects.count()} messages."
            )
        )
