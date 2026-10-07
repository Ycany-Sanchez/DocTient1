from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import redirect, render

from apps.clinic.models import DoctorProfile, Message, PatientProfile


def _my_role(user):
    if DoctorProfile.objects.filter(user=user).exists():
        return "doctor"
    if PatientProfile.objects.filter(user=user).exists():
        return "patient"
    return None


def _eligible_recipients(user, role):
    """Cross-role only: patients <-> doctors."""
    if role == "patient":
        return User.objects.filter(doctor_profile__isnull=False).order_by("username")[:50]
    if role == "doctor":
        return User.objects.filter(patient_profile__isnull=False).order_by("username")[:50]
    return User.objects.none()


@login_required
def messages_view(request):
    role = _my_role(request.user)
    if role is None:
        django_messages.info(request, "Pick a role first.")
        return redirect("home:home")

    # All messages involving me, newest first for conversation list.
    all_mine = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).select_related("sender", "recipient").order_by("-sent_at")[:200]

    # Build conversation list: counterpart -> {user, last_message, unread}.
    conversations = {}
    for m in all_mine:
        other = m.recipient if m.sender_id == request.user.id else m.sender
        entry = conversations.get(other.id)
        if entry is None:
            entry = {"user": other, "last_message": m, "unread": 0}
            conversations[other.id] = entry
        if m.recipient_id == request.user.id and not m.is_read:
            entry["unread"] += 1
    conversation_list = sorted(
        conversations.values(), key=lambda c: c["last_message"].sent_at, reverse=True
    )
    total_unread = sum(c["unread"] for c in conversation_list)

    active_name = (request.GET.get("with") or "").strip()
    active_user = None
    thread = []
    if active_name:
        try:
            active_user = User.objects.get(username=active_name)
        except User.DoesNotExist:
            django_messages.error(request, f"No user '{active_name}'.")
            return redirect("messages:messages")
        if active_user.id == request.user.id:
            django_messages.error(request, "You cannot message yourself.")
            return redirect("messages:messages")
        # Enforce cross-role messaging.
        other_role = _my_role(active_user)
        if role == other_role:
            django_messages.error(request, "Patients can only message doctors and vice versa.")
            return redirect("messages:messages")

    if request.method == "POST":
        to_name = (request.POST.get("recipient") or active_name or "").strip()
        content = (request.POST.get("content") or "").strip()
        if not to_name or not content:
            django_messages.error(request, "Choose a recipient and write a message.")
            return redirect("messages:messages" + (f"?with={to_name}" if to_name else ""))
        try:
            to_user = User.objects.get(username=to_name)
        except User.DoesNotExist:
            django_messages.error(request, f"No user '{to_name}'.")
            return redirect("messages:messages")
        if to_user.id == request.user.id or _my_role(to_user) == role:
            django_messages.error(request, "Patients can only message doctors and vice versa.")
            return redirect("messages:messages")
        Message.objects.create(sender=request.user, recipient=to_user, content=content)
        return redirect(f"/messages/?with={to_user.username}")

    if active_user:
        thread = list(
            Message.objects.filter(
                Q(sender=request.user, recipient=active_user)
                | Q(sender=active_user, recipient=request.user)
            ).select_related("sender", "recipient").order_by("sent_at")[:200]
        )
        # Mark their messages to me as read.
        Message.objects.filter(
            sender=active_user, recipient=request.user, is_read=False
        ).update(is_read=True)

    return render(request, "messages/messages.html", {
        "role": role,
        "conversations": conversation_list,
        "total_unread": total_unread,
        "active_user": active_user,
        "thread": thread,
        "recipients": _eligible_recipients(request.user, role),
    })
