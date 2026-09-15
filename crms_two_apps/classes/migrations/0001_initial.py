from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("students", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClassRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "subject_code",
                    models.CharField(
                        max_length=20,
                        unique=True,
                    ),
                ),
                (
                    "subject_name",
                    models.CharField(max_length=200),
                ),
                (
                    "schedule",
                    models.CharField(
                        blank=True,
                        max_length=200,
                    ),
                ),
                (
                    "room",
                    models.CharField(
                        blank=True,
                        max_length=100,
                    ),
                ),
            ],
            options={
                "ordering": ["subject_code"],
            },
        ),
        migrations.CreateModel(
            name="Enrollment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "enrolled_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "class_record",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enrollments",
                        to="classes.classrecord",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enrollments",
                        to="students.student",
                    ),
                ),
            ],
            options={
                "ordering": [
                    "student__last_name",
                    "student__first_name",
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="enrollment",
            constraint=models.UniqueConstraint(
                fields=("student", "class_record"),
                name="unique_student_class",
            ),
        ),
    ]
