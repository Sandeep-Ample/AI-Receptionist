okay i have finaliez my database schema to this: -- =====================================================
-- HOSPITAL AI VOICE AGENT – FINAL OPTIMIZED SCHEMA
-- =====================================================

-- =========================
-- ENUM TYPES
-- =========================
CREATE TYPE appointment_status_enum AS ENUM
('Booked', 'Scheduled', 'Completed', 'Cancelled', 'NoShow', 'Rescheduled');

CREATE TYPE shift_status_enum AS ENUM
('Active', 'Inactive', 'OnLeave');

CREATE TYPE doctor_status_enum AS ENUM
('Active', 'Inactive', 'Retired');

CREATE TYPE gender_enum AS ENUM
('Male', 'Female', 'Other');

CREATE TYPE weekday_enum AS ENUM
('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday');

-- =========================
-- PATIENT ACCOUNT
-- =========================
CREATE TABLE patient_account (
    account_id serial PRIMARY KEY,
    mobile_no varchar(15) NOT NULL UNIQUE,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- =========================
-- PATIENT
-- =========================
CREATE TABLE patient (
    pt_id serial PRIMARY KEY,
    account_id integer NOT NULL REFERENCES patient_account(account_id),
    name varchar(100) NOT NULL,
    gender gender_enum,
    dob date,
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- =========================
-- SPECIALTY
-- =========================
CREATE TABLE specialty (
    spec_id serial PRIMARY KEY,
    spec_name varchar(100) NOT NULL UNIQUE
);

-- =========================
-- SYMPTOMS
-- =========================
CREATE TABLE symptoms (
    sym_id serial PRIMARY KEY,
    sym_name varchar(100) NOT NULL UNIQUE
);

-- =========================
-- DOCTOR
-- =========================
CREATE TABLE doctor (
    doc_id serial PRIMARY KEY,
    name varchar(100) NOT NULL,
    address text,
    experiences integer CHECK (experiences >= 0),
    degree_doc varchar(100),
    status doctor_status_enum DEFAULT 'Active',
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- =========================
-- DOCTOR ↔ SPECIALTY (M:N)
-- =========================
CREATE TABLE doctor_specialty (
    doc_id integer REFERENCES doctor(doc_id) ON DELETE CASCADE,
    spec_id integer REFERENCES specialty(spec_id) ON DELETE CASCADE,
    PRIMARY KEY (doc_id, spec_id)
);

-- =========================
-- DOCTOR SHIFT
-- =========================
CREATE TABLE doc_shift (
    shft_id serial PRIMARY KEY,
    doc_id integer NOT NULL REFERENCES doctor(doc_id),
    day_of_week weekday_enum NOT NULL,
    start_time time NOT NULL,
    end_time time NOT NULL,
    status shift_status_enum DEFAULT 'Active',
    CHECK (start_time < end_time)
);

-- =========================
-- APPOINTMENT
-- =========================
CREATE TABLE appointment (
    app_id serial PRIMARY KEY,
    account_id integer NOT NULL REFERENCES patient_account(account_id),
    pt_id integer NOT NULL REFERENCES patient(pt_id),
    doc_id integer NOT NULL REFERENCES doctor(doc_id),
    reason text,
    date_time timestamp NOT NULL,
    app_status appointment_status_enum DEFAULT 'Booked',
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Prevent double booking
CREATE UNIQUE INDEX ux_doctor_appointment_time
ON appointment (doc_id, date_time)
WHERE app_status NOT IN ('Cancelled', 'NoShow');

-- =========================
-- PATIENT MEMORY (AI SUMMARY)
-- =========================
CREATE TABLE patient_memory (
    pm_id serial PRIMARY KEY,
    app_id integer REFERENCES appointment(app_id) ON DELETE CASCADE,
    summary text
);

-- =========================
-- SPECIALTY ↔ SYMPTOMS (AI INFERENCE)
-- =========================
CREATE TABLE spec_sym (
    spec_id integer REFERENCES specialty(spec_id) ON DELETE CASCADE,
    sym_id integer REFERENCES symptoms(sym_id) ON DELETE CASCADE,
    confidence numeric(3,2) DEFAULT 1.0,
    PRIMARY KEY (spec_id, sym_id)
);

-- =========================
-- USER MEMORY (VOICE AGENT MEMORY)
-- =========================
CREATE TABLE user_memory (
    phone_number varchar(64) PRIMARY KEY,
    name varchar(128),
    last_summary text,
    last_call timestamptz DEFAULT now(),
    call_count integer DEFAULT 1,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE INDEX idx_user_memory_last_call
ON user_memory (last_call DESC);

-- =========================
-- CALL SESSION (AI CORE)
-- =========================
CREATE TABLE call_session (
    session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number varchar(64),
    started_at timestamptz DEFAULT now(),
    ended_at timestamptz,
    intent text,
    outcome text,
    transcript text,
    confidence_score numeric(3,2)
);

-- =========================
-- SEARCH & AI PERFORMANCE INDEXES
-- =========================
CREATE INDEX idx_patient_account_mobile ON patient_account(mobile_no);
CREATE INDEX idx_doctor_name ON doctor(name);
CREATE INDEX idx_specialty_name ON specialty(spec_name);
CREATE INDEX idx_symptoms_name ON symptoms(sym_name);

-- =========================
-- UPDATED_AT AUTO-UPDATE
-- =========================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_patient_updated
BEFORE UPDATE ON patient
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_doctor_updated
BEFORE UPDATE ON doctor
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_appointment_updated
BEFORE UPDATE ON appointment
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_user_memory_updated
BEFORE UPDATE ON user_memory
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- END OF FINAL SCHEMA
-- ===================================================== 




# 📘 Hospital AI Voice Agent – Database Summary & Data Model Documentation

## 1. Overview

This database models a **real-world hospital appointment system integrated with an AI voice agent**.
It is designed to handle:

* Patient registration via phone numbers
* Multiple patients per account (family-based model)
* Doctors with multiple specialties and shifts
* Appointment scheduling with strict no-double-booking rules
* AI-driven symptom → specialty inference
* Voice agent memory and call session tracking

The schema enforces **real hospital constraints**, supports **high-volume data**, and is optimized for **AI, analytics, and production workloads**.

---

## 2. Core Design Principles

* **Phone number–first system** (voice agent compatible)
* **Slot-based appointment scheduling**
* **Strong referential integrity**
* **AI-ready memory & inference tables**
* **Realistic hospital workflows**

---

## 3. Entity Overview

### Main Entities

| Entity          | Purpose                               |
| --------------- | ------------------------------------- |
| patient_account | Represents a caller or family account |
| patient         | Individual patients under an account  |
| doctor          | Doctors practicing at the hospital    |
| specialty       | Medical specialties                   |
| symptoms        | Patient-reported symptoms             |
| appointment     | Scheduled doctor visits               |
| doc_shift       | Doctor availability                   |
| user_memory     | Voice AI long-term memory             |
| call_session    | Individual AI call logs               |

---

## 4. Table-by-Table Explanation

---

### 4.1 patient_account

**Represents a unique phone number interacting with the hospital**

```text
One patient_account can have multiple patients (family members)
```

**Key Columns**

* `account_id` – primary identifier
* `mobile_no` – unique phone number
* `created_at`, `updated_at` – audit fields

**Used by**

* patient
* appointment
* user_memory
* call_session

---

### 4.2 patient

**Represents an individual patient**

```text
One account → many patients
One patient → many appointments
```

**Key Columns**

* `pt_id` – patient ID
* `account_id` – links to patient_account
* `name`, `gender`, `dob`
* `is_active`

---

### 4.3 specialty

**Medical departments / areas of expertise**

Examples:

* Cardiology
* Dermatology
* Neurology
* Pediatrics

**Relationships**

* Many-to-many with doctors
* Many-to-many with symptoms (AI inference)

---

### 4.4 symptoms

**Standardized symptom vocabulary**

Examples:

* Fever
* Chest Pain
* Migraine
* Anxiety

Used by AI to infer appropriate specialties.

---

### 4.5 doctor

**Represents a medical professional**

**Key Columns**

* `doc_id`
* `name`
* `experience`
* `degree_doc`
* `status` (Active / Inactive / Retired)

**Relationships**

* Many specialties
* Many shifts
* Many appointments

---

### 4.6 doctor_specialty (M:N)

**Maps doctors to one or more specialties**

```text
Doctor A → Cardiology + General Medicine
Doctor B → Orthopedics only
```

This reflects real-world multi-specialty doctors.

---

### 4.7 doc_shift

**Defines doctor working hours**

```text
One doctor → many shifts
Each shift = one weekday + time range
```

Used to:

* Calculate availability
* Generate valid appointment slots

---

### 4.8 appointment

**Central transactional table**

```text
One patient → many appointments
One doctor → many appointments
One doctor → one appointment per time slot
```

**Key Columns**

* `date_time` – exact appointment slot
* `app_status` – Booked, Completed, Cancelled, NoShow
* `reason`

#### 🚫 Double Booking Prevention

A **partial unique index** enforces:

```text
A doctor cannot have two active appointments at the same time
```

Cancelled or NoShow appointments do not block slots.

---

### 4.9 patient_memory

**AI-generated clinical summaries**

```text
One appointment → zero or one memory
```

Stores:

* Doctor notes
* AI summaries
* Context for future visits

---

### 4.10 spec_sym

**AI inference mapping between symptoms and specialties**

Each mapping includes a `confidence` score.

Example:

* Chest Pain → Cardiology (0.92)
* Anxiety → Psychiatry (0.88)

Used for:

* AI doctor recommendations
* Voice agent triaging

---

### 4.11 user_memory

**Long-term AI memory per phone number**

Tracks:

* Caller name
* Last conversation summary
* Call count
* Metadata (JSON)

This allows the voice agent to:

* Remember returning users
* Continue conversations naturally

---

### 4.12 call_session

**Individual AI voice calls**

Each record logs:

* Call intent
* Outcome
* Transcript
* Confidence score

Used for:

* AI quality monitoring
* Analytics
* Retraining models

---

## 5. How Data Is Seeded (Realistic Simulation)

### Doctors

* 40 doctors
* Each assigned 1–4 specialties
* 9 AM–5 PM shifts for all weekdays

### Patients

* 200 phone accounts
* 1–2 patients per account (family model)

### Appointments

* Slot-based (15-minute intervals)
* Generated across 30–60 days
* No doctor double booking
* Realistic mix of:

  * Completed
  * Booked
  * Cancelled
  * NoShow

### AI Data

* Symptoms mapped to specialties
* Patient memory created for completed visits
* Call sessions generated for each user

---

## 6. Relationship Diagram (Textual)

```text
patient_account
  └── patient
        └── appointment ─── doctor
                               ├── doctor_specialty ─── specialty
                               └── doc_shift

specialty ─── spec_sym ─── symptoms

appointment ─── patient_memory

patient_account ─── user_memory
patient_account ─── call_session
```

---

## 7. Why This Schema Is Production-Ready

✔ Enforces real hospital constraints
✔ Scales to millions of appointments
✔ AI-friendly memory & inference design
✔ Analytics & reporting ready
✔ Voice agent compatible
✔ Safe incremental data growth

---

## 8. Ideal Use Cases

* AI voice appointment booking
* Doctor recommendation systems
* Hospital dashboards
* Call center automation
* Healthcare analytics
* AI training datasets

---

## 9. Summary

This database accurately models **real hospital operations combined with AI voice interactions**.
It balances **data integrity**, **performance**, and **AI-readiness**, making it suitable for both **production systems and research/training environments**.

---

**End of Documentation**
