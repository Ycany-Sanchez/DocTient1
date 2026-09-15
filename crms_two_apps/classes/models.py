from django.db import models

from students.models import Student


class ClassRecord(models.Model):
    subject_code = models.CharField(
        max_length=20,
        unique=True,
    )
    subject_name = models.CharField(max_length=200)
    schedule = models.CharField(max_length=200, blank=True)
    room = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["subject_code"]

    def __str__(self):
        return f"{self.subject_code} - {self.subject_name}"


class Enrollment(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    class_record = models.ForeignKey(
        ClassRecord,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "class_record"],
                name="unique_student_class",
            )
        ]
        ordering = ["student__last_name", "student__first_name"]

    def __str__(self):
        return (
            f"{self.student} -> {self.class_record}"
        )
