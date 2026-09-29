from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

def _user_role_label(self):
    if DoctorProfile.objects.filter(user_id=self.pk).exists():
        return 'doctor'
    if PatientProfile.objects.filter(user_id=self.pk).exists():
        return 'patient'
    if self.is_superuser:
        return 'admin'
    return 'patient'


User.add_to_class('role_label', property(_user_role_label))


class PatientProfile(models.Model):
    """ERD: PATIENT_PROFILES. Extends USER as patient (1-1)."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='patient_profile'
    )
    full_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    contact_no = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=100, blank=True)
    emergency_contact_no = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'patient_profiles'

    def __str__(self):
        return f"{self.full_name} ({self.user.username})"


class DoctorProfile(models.Model):
    """ERD: DOCTOR_PROFILE. Extends USER as doctor (1-1)."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='doctor_profile'
    )
    full_name = models.CharField(max_length=100)
    med_specialty = models.CharField(max_length=100, blank=True)
    contact_no = models.CharField(max_length=20, blank=True)
    availability_status = models.CharField(max_length=20, default='available')
    bio = models.TextField(blank=True)

    class Meta:
        db_table = 'doctor_profiles'

    def __str__(self):
        return f"Dr. {self.full_name} ({self.med_specialty})"


class VitalSign(models.Model):
    """ERD: VITAL_SIGNS. PATIENT_PROFILES 1-M records."""
    patient = models.ForeignKey(
        PatientProfile, on_delete=models.CASCADE, related_name='vital_signs'
    )
    systolic = models.IntegerField(null=True, blank=True)
    diastolic = models.IntegerField(null=True, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True)
    temperature_celsius = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    oxygen_saturation = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    weight_kg = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    monitoring_status = models.CharField(max_length=20, blank=True)
    patient_notes = models.TextField(blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'vital_signs'
        ordering = ['-recorded_at']

    def __str__(self):
        return f"Vitals {self.id} for {self.patient_id} @ {self.recorded_at}"


class Message(models.Model):
    """ERD: MESSAGES. USER 1-M sends/receives (sender + recipient FKs)."""
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_messages'
    )
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='received_messages'
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'messages'
        ordering = ['-sent_at']

    def __str__(self):
        return f"Msg {self.id}: {self.sender_id}->{self.recipient_id}"


class Medication(models.Model):
    """ERD: MEDICATIONS. Patient receives, Doctor prescribes."""
    patient = models.ForeignKey(
        PatientProfile, on_delete=models.CASCADE, related_name='medications'
    )
    doctor = models.ForeignKey(
        DoctorProfile, on_delete=models.CASCADE,
        related_name='prescribed_medications', null=True, blank=True
    )
    medication = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50, blank=True)
    frequency = models.CharField(max_length=50, blank=True)
    scheduled_time = models.TimeField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    reminder_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'medications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.medication} for patient {self.patient_id}"


class MedicationLog(models.Model):
    """ERD: MEDICATION_LOGS. MEDICATIONS 1-M logs."""
    medication = models.ForeignKey(
        Medication, on_delete=models.CASCADE, related_name='logs'
    )
    taken_at = models.DateTimeField(null=True, blank=True)
    is_taken = models.BooleanField(default=False)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = 'medication_logs'
        ordering = ['-scheduled_for']

    def __str__(self):
        return f"Log {self.id} med={self.medication_id} taken={self.is_taken}"


class DoctorNote(models.Model):
    """ERD: DOCTOR_NOTES. DOCTOR_PROFILE 1-M authors."""
    doctor = models.ForeignKey(
        DoctorProfile, on_delete=models.CASCADE, related_name='notes'
    )
    observations = models.TextField()
    recommendations = models.TextField(blank=True)

    class Meta:
        db_table = 'doctor_notes'

    def __str__(self):
        return f"Note {self.id} by doctor {self.doctor_id}"


class DoctorPatientConnection(models.Model):
    """ERD: DOCTOR_PATIENT_CONNECTIONS. Doctor M-M Patient link."""
    doctor = models.ForeignKey(
        DoctorProfile, on_delete=models.CASCADE, related_name='patient_connections'
    )
    patient = models.ForeignKey(
        PatientProfile, on_delete=models.CASCADE, related_name='doctor_connections'
    )
    observations = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'doctor_patient_connections'
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'patient'], name='unique_doctor_patient'
            )
        ]

    def __str__(self):
        return f"Conn doc={self.doctor_id} pat={self.patient_id}"
