import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from students.models import Student

from .forms import ClassRecordForm
from .models import ClassRecord, Enrollment


def class_list(request):
    classes = ClassRecord.objects.all()

    return render(
        request,
        "classes/list.html",
        {
            "classes": classes,
        },
    )


def class_detail(request, class_id):
    class_record = get_object_or_404(
        ClassRecord,
        id=class_id,
    )

    enrollments = (
        Enrollment.objects
        .filter(class_record=class_record)
        .select_related("student")
    )

    available_students = (
        Student.objects
        .exclude(
            id__in=enrollments.values_list(
                "student_id",
                flat=True,
            )
        )
        .order_by("last_name", "first_name")
    )

    return render(
        request,
        "classes/detail.html",
        {
            "class_record": class_record,
            "enrollments": enrollments,
            "available_students": available_students,
        },
    )


def class_create(request):
    if request.method == "POST":
        form = ClassRecordForm(request.POST)

        if form.is_valid():
            class_record = form.save()
            messages.success(
                request,
                f"{class_record.subject_code} was created.",
            )
            return redirect(
                "classes:detail",
                class_id=class_record.id,
            )
    else:
        form = ClassRecordForm()

    return render(
        request,
        "classes/form.html",
        {
            "form": form,
        },
    )


@require_GET
def class_students_json(request, class_id):
    class_record = get_object_or_404(
        ClassRecord,
        id=class_id,
    )

    enrollments = (
        Enrollment.objects
        .filter(class_record=class_record)
        .select_related("student")
    )

    students = [
        {
            "id": enrollment.student.id,
            "student_id": enrollment.student.student_id,
            "name": (
                f"{enrollment.student.first_name} "
                f"{enrollment.student.last_name}"
            ),
            "email": enrollment.student.email,
        }
        for enrollment in enrollments
    ]

    return JsonResponse(
        {
            "class_id": class_record.id,
            "subject_code": class_record.subject_code,
            "subject_name": class_record.subject_name,
            "students": students,
        }
    )


@require_POST
def enroll_student(request, class_id):
    class_record = get_object_or_404(
        ClassRecord,
        id=class_id,
    )

    try:
        data = json.loads(request.body)
        student_id = data.get("student_id")
    except (json.JSONDecodeError, TypeError):
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid JSON request.",
            },
            status=400,
        )

    if not student_id:
        return JsonResponse(
            {
                "success": False,
                "message": "student_id is required.",
            },
            status=400,
        )

    student = get_object_or_404(
        Student,
        id=student_id,
    )

    enrollment, created = Enrollment.objects.get_or_create(
        student=student,
        class_record=class_record,
    )

    return JsonResponse(
        {
            "success": True,
            "created": created,
            "message": (
                f"{student.first_name} {student.last_name} "
                f"{'was enrolled.' if created else 'is already enrolled.'}"
            ),
            "enrollment_id": enrollment.id,
        }
    )
