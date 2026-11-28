# DocTient — Clinical Telehealth & Biometric Telemetry Platform

DocTient is a role-isolated telehealth web application built with **Python Django 6.1** and **Supabase PostgreSQL**. It supports patient self-monitoring, physician cohort oversight, medication adherence tracking, clinical reporting, and doctor–patient messaging.

## Architecture (Vertical Slicing)

```text
DocTient/
├── config/                 # Project settings, root URLs, WSGI/ASGI
├── apps/
│   ├── clinic/             # Core ERD models + management commands
│   ├── login/              # Authentication views & landing UI
│   ├── register/           # Role-based account registration (patient / doctor)
│   ├── home/               # Role-isolated Patient & Doctor Dashboards
│   ├── reports/            # Clinical analytics, risk stratification, CSV export
│   ├── messaging/          # Cross-role doctor <-> patient inbox & threads
│   ├── user_profile/       # Patient demographics/biometrics & doctor credentials
│   └── user_settings/      # Theme (dark mode) & notification preferences
├── templates/              # Framed Sheet clinical shell & page templates
├── static/                 # CSS design system, canvas charting, telemetry JS
└── supabase_schema.sql     # PostgreSQL physical ERD reference DDL
```

## Database Schema (Supabase PostgreSQL)

Core tables managed in `apps/clinic/models.py` alongside Django `auth_user`:

- `patient_profiles` (1:1 with `auth_user`)
- `doctor_profiles` (1:1 with `auth_user`)
- `vital_signs` (1:M from `patient_profiles`)
- `medications` (M:1 to `patient_profiles` and `doctor_profiles`)
- `medication_logs` (1:M from `medications`)
- `doctor_patient_connections` (M:M link with clinical observations & care plans)
- `doctor_notes` (1:M from `doctor_profiles`)
- `messages` (1:M sender/recipient on `auth_user`)

## Local Setup

1. **Create and activate a virtual environment** (from `DocTient1/`):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r DocTient/requirements.txt
   ```

2. **Configure environment variables** (`DocTient/.env`):

   ```bash
   cp DocTient/.env.example DocTient/.env
   # Set DATABASE_URL to your Supabase PostgreSQL pooler connection string
   ```

3. **Run migrations and seed demo data**:

   ```bash
   cd DocTient
   python manage.py migrate
   python manage.py seed_doctient_data
   ```

4. **Start the development server**:

   ```bash
   python manage.py runserver
   ```

   Open `http://127.0.0.1:8000/login/`.

## Useful Commands

```bash
# Run full test suite (uses isolated in-memory SQLite when DATABASE_URL is unset)
DATABASE_URL="" python manage.py test -v 2

# Print live SQL JOIN and SUBQUERY diagnostics against Supabase
python manage.py verify_sql_activity
```
