from django import forms

from .models import ClassRecord


class ClassRecordForm(forms.ModelForm):
    class Meta:
        model = ClassRecord
        fields = [
            "subject_code",
            "subject_name",
            "schedule",
            "room",
        ]
