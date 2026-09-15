from django.db import models


class Student(models.Model):
    student_id = models.CharField(
        max_length=20,
        unique=True,
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.student_id} - {self.first_name} {self.last_name}"
