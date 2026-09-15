from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import StudentForm
from .models import Student


@login_required
def student_list(request):
    students = Student.objects.all()
    return render(
        request,
        "students/list.html",
        {
            "students": students,
        },
    )


@login_required
def student_detail(request, student_id):
    student = get_object_or_404(
        Student,
        id=student_id,
    )
    return render(
        request,
        "students/detail.html",
        {
            "student": student,
        },
    )


@login_required
def student_create(request):
    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(
                request,
                f"Student {student.first_name} {student.last_name} was created.",
            )
            return redirect("students:detail", student_id=student.id)
    else:
        form = StudentForm()

    return render(
        request,
        "students/form.html",
        {
            "form": form,
        },
    )
