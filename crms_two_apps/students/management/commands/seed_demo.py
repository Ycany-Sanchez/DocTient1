from django.core.management.base import BaseCommand

from classes.models import ClassRecord, Enrollment
from students.models import Student


class Command(BaseCommand):
    help = "Creates sample Students, Classes, and Enrollments."

    def handle(self, *args, **options):
        students_data = [
            ("20260001", "Juan", "Dela Cruz", "juan@example.com"),
            ("20260002", "Maria", "Santos", "maria@example.com"),
            ("20260003", "Pedro", "Reyes", "pedro@example.com"),
            ("20260004", "Ana", "Garcia", "ana@example.com"),
        ]

        students = []

        for student_id, first_name, last_name, email in students_data:
            student, _ = Student.objects.update_or_create(
                student_id=student_id,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                },
            )
            students.append(student)

        classes_data = [
            ("IT101", "Introduction to Computing", "MWF 8:00-9:00 AM", "Room 301"),
            ("IT202", "Web Development", "TTh 10:00-11:30 AM", "Room 205"),
            ("IT303", "Database Systems", "MWF 1:00-2:00 PM", "Room 402"),
        ]

        class_records = []

        for code, name, schedule, room in classes_data:
            class_record, _ = ClassRecord.objects.update_or_create(
                subject_code=code,
                defaults={
                    "subject_name": name,
                    "schedule": schedule,
                    "room": room,
                },
            )
            class_records.append(class_record)

        enrollment_pairs = [
            (students[0], class_records[0]),
            (students[0], class_records[1]),
            (students[1], class_records[0]),
            (students[1], class_records[2]),
            (students[2], class_records[1]),
            (students[2], class_records[2]),
            (students[3], class_records[0]),
        ]

        for student, class_record in enrollment_pairs:
            Enrollment.objects.get_or_create(
                student=student,
                class_record=class_record,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data created successfully."
            )
        )
