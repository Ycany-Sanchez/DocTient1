-- ============================================================
-- DocTient Physical ERD -> Supabase (PostgreSQL) DDL
-- Source: 📢 ANNOUNCEMENT_ PHYSICAL ERD SUBMISSION.pdf
-- SANCHEZ, CSIT 327-F2
--
-- Paste this in: Supabase Dashboard -> SQL Editor -> New query -> Run
-- This follows your ERD literally (bigint PK, varchar/text/date/time/
-- timestamp/boolean/int/decimal-5-2, FK relationships).
--
-- NOTE on Django mapping:
--   ERD USER  -> Django auth.User (table auth_user, created by migrate).
--   The `users` table below is for ERD compliance / manual review.
--   OPERATIONAL PATH (recommended): set DATABASE_URL in .env, then run
--   `python manage.py migrate` — Django creates auth_user +
--   patient_profiles, doctor_profiles, vital_signs, messages,
--   medications, medication_logs, doctor_notes,
--   doctor_patient_connections with the same FK structure.
--   If you run `migrate`, DO NOT also run the `users` section blindly
--   or you will have two user tables. Pick ONE path (see bottom).
-- ============================================================

-- ---------- PATH A: ERD-faithful tables (for professor check) ----------

CREATE TABLE IF NOT EXISTS users (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  username VARCHAR(100) NOT NULL UNIQUE,
  email VARCHAR(100) NOT NULL UNIQUE,
  password VARCHAR(100) NOT NULL,
  role VARCHAR(50) NOT NULL DEFAULT 'patient'
    CHECK (role IN ('patient', 'doctor', 'admin'))
);

CREATE TABLE IF NOT EXISTS patient_profiles (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  full_name VARCHAR(100) NOT NULL,
  date_of_birth DATE,
  gender VARCHAR(20),
  height_cm DECIMAL(5,2),
  weight_kg DECIMAL(5,2),
  contact_no VARCHAR(20),
  address VARCHAR(100),
  emergency_contact_no VARCHAR(20)
);
-- ERD: USER 1-1 extends as patient

CREATE TABLE IF NOT EXISTS doctor_profiles (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  full_name VARCHAR(100) NOT NULL,
  med_specialty VARCHAR(100),
  contact_no VARCHAR(20),
  availability_status VARCHAR(20) NOT NULL DEFAULT 'available',
  bio TEXT
);
-- ERD: USER 1-1 extends as doctor

CREATE TABLE IF NOT EXISTS vital_signs (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  patient_id BIGINT NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,
  systolic INT,
  diastolic INT,
  heart_rate INT,
  temperature_celsius DECIMAL(5,2),
  oxygen_saturation DECIMAL(5,2),
  weight_kg DECIMAL(5,2),
  monitoring_status VARCHAR(20),
  patient_notes TEXT,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- ERD: PATIENT_PROFILES 1-M records
CREATE INDEX IF NOT EXISTS idx_vitals_patient ON vital_signs(patient_id);

CREATE TABLE IF NOT EXISTS messages (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sender_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  recipient_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- ERD: USER 1-M sends/receives
CREATE INDEX IF NOT EXISTS idx_msg_sender ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_msg_recipient ON messages(recipient_id);

CREATE TABLE IF NOT EXISTS medications (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  patient_id BIGINT NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,
  doctor_id BIGINT REFERENCES doctor_profiles(id) ON DELETE CASCADE,
  medication VARCHAR(100) NOT NULL,
  dosage VARCHAR(50),
  frequency VARCHAR(50),
  scheduled_time TIME,
  start_date DATE,
  end_date DATE,
  reminder_active BOOLEAN NOT NULL DEFAULT TRUE,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- ERD: patient receives, doctor prescribes
CREATE INDEX IF NOT EXISTS idx_meds_patient ON medications(patient_id);
CREATE INDEX IF NOT EXISTS idx_meds_doctor ON medications(doctor_id);

CREATE TABLE IF NOT EXISTS medication_logs (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  medication_id BIGINT NOT NULL REFERENCES medications(id) ON DELETE CASCADE,
  taken_at TIMESTAMPTZ,
  is_taken BOOLEAN NOT NULL DEFAULT FALSE,
  scheduled_for TIMESTAMPTZ,
  remarks TEXT
);
-- ERD: MEDICATIONS 1-M logs
CREATE INDEX IF NOT EXISTS idx_medlogs_med ON medication_logs(medication_id);

CREATE TABLE IF NOT EXISTS doctor_notes (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  doctor_id BIGINT NOT NULL REFERENCES doctor_profiles(id) ON DELETE CASCADE,
  observations TEXT NOT NULL,
  recommendations TEXT
);
-- ERD: DOCTOR_PROFILE 1-M authors
CREATE INDEX IF NOT EXISTS idx_notes_doctor ON doctor_notes(doctor_id);

CREATE TABLE IF NOT EXISTS doctor_patient_connections (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  doctor_id BIGINT NOT NULL REFERENCES doctor_profiles(id) ON DELETE CASCADE,
  patient_id BIGINT NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,
  observations TEXT,
  recommendations TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (doctor_id, patient_id)
);
-- ERD: connects many patients / many doctors
CREATE INDEX IF NOT EXISTS idx_conn_doctor ON doctor_patient_connections(doctor_id);
CREATE INDEX IF NOT EXISTS idx_conn_patient ON doctor_patient_connections(patient_id);

-- ---------- PATH B: Django operational (use instead if you run migrate) ----------
-- If you connect Django via DATABASE_URL and run `migrate`, Django creates:
--   auth_user, patient_profiles, doctor_profiles, vital_signs, messages,
--   medications, medication_logs, doctor_notes, doctor_patient_connections
-- with FKs to auth_user(id) instead of users(id).
-- In that case SKIP the `users` table above to avoid duplication.
-- Verify after migrate with:
--   SELECT table_name FROM information_schema.tables
--   WHERE table_schema='public' ORDER BY 1;
