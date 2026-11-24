from apps.clinic.models import DoctorProfile, Message, PatientProfile
from apps.user_settings.models import UserSettings


def shell_context(request):
    """Provides theme preference, unread message count, and profile summary for the app shell."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {
            "user_dark_mode": False,
            "nav_unread_count": 0,
            "nav_display_name": "",
            "nav_role_label": "",
            "nav_initials": "",
        }

    user = request.user
    settings_obj = UserSettings.objects.filter(user=user).first()
    dark_mode = bool(settings_obj.dark_mode) if settings_obj else False

    unread_count = Message.objects.filter(recipient=user, is_read=False).count()

    doctor = DoctorProfile.objects.filter(user=user).first()
    patient = PatientProfile.objects.filter(user=user).first()
    if doctor:
        display_name = doctor.full_name or user.username
        role_label = doctor.med_specialty or "Attending Physician"
    elif patient:
        display_name = patient.full_name or user.username
        role_label = "Patient"
    else:
        display_name = user.username
        role_label = "Account"

    parts = [p for p in display_name.replace(".", " ").split() if p]
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[-1][0]).upper()
    elif parts:
        initials = parts[0][:2].upper()
    else:
        initials = user.username[:2].upper()

    return {
        "user_dark_mode": dark_mode,
        "nav_unread_count": unread_count,
        "nav_display_name": display_name,
        "nav_role_label": role_label,
        "nav_initials": initials,
    }
