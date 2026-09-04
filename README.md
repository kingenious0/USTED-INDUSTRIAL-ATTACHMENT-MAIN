# USTED Industrial Attachment Management System (U-IAP) Core MVP

The **U-IAP Core System** digitizes the administrative lifecycle of Workplace Experience Learning (WEL) / industrial attachment for the **University of Skills Training and Entrepreneurial Development (USTED)** Industrial Liaison Unit.

The system conforms to the approved PRD (Product Requirements Document), preserving institutionally mandatory physical procedures (official wet-ink company stamps, physical supervisor evaluations, and sealed assessments) while providing a robust, server-enforced digital workflow.

---

## Key Features & Architecture

1. **Physical Liaison Intake Checkpoint:**
   - In-person student verification and index lookup in the university student master dataset.
   - Levels 100, 200, 300, and 400 are supported (no artificial Level 300 restriction).
   - Attachment record creation with automatic provisioning of weekly activity sheets.
2. **Standardized Document Engine (ReportLab):**
   - Official Introductory Letter generation with tracking reference numbers and reprint counting.
   - Blank physical WEL Acceptance Form template generation.
   - Weekly Activity Sheet PDF with dedicated **Physical Workplace Supervisor Verification Section** (supervisor comments, signature, verification date, and official company wet-ink stamp box).
   - Multi-Week Compiled Activity Document for attachment closeout.
3. **Acceptance Form Upload & Institutional Review:**
   - Secure scan upload (PDF, PNG, JPG, JPEG) with backend MIME and size validation.
   - Liaison review queue enforcing wet-ink company stamp and signature checks before approval.
   - Configurable policy toggle (`REQUIRE_ACCEPTANCE_APPROVAL_BEFORE_LOGGING`) accommodating both Option A (strict approval needed before logging) and Option B (asynchronous review while logging proceeds).
4. **Monday–Friday Activity Logger & Student Locking:**
   - Expandable activity fields (Key Tasks, Skills Demonstrated, Remarks) without physical paper line constraints.
   - Student controls when the week is locked (no automatic Friday or time-based locks).
   - **Strict server-side read-only enforcement:** once locked, all entries become immutable on the server.
5. **REST API Interface (`/api/v1`):**
   - Designed for future integration with the existing mobile/web eLogSheet without tight coupling.
6. **Institutional Audit Trail & RBAC:**
   - Granular roles: Student, Liaison Officer, Liaison Head / Admin, Academic Supervisor.
   - Audit logging for all critical operations (logins, attachment initiation, letter reprints, acceptance reviews, weekly locks, configuration updates).

---

## Quick Start (Local Development)

### 1. Prerequisites

- Python 3.12+
- Pip

### 2. Setup Virtual Environment

```bash
# In "USTED INDUSTRIAL ATTACHMENT(U-IAP MAIN)"
python -m venv venv
.\venv\Scripts\activate   # Windows
# or source venv/bin/activate on Linux/Mac
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize Database & Seed Demo Data

```bash
python run.py
```

This automatically initializes the SQLite database (`u_iap.db`), provisions schema tables, and seeds initial demo users and student master records.

### 5. Access the Portal

Open your browser and navigate to:

```
http://127.0.0.1:5000
```

---

## Pre-Seeded Testing Accounts

| Role                              | Username        | Password        | Notes                                                                                                  |
| --------------------------------- | --------------- | --------------- | ------------------------------------------------------------------------------------------------------ |
| **Liaison Officer**         | `liaison1`    | `password123` | Can search students, verify identity, create attachments, reprint letters, and review acceptance scans |
| **Liaison Head / Admin**    | `admin1`      | `password123` | Full administrative privileges, audit logs viewer, and policy toggle settings                          |
| **Student (Level 300 IT)**  | `student1`    | `password123` | Linked to Index`USTED/2024/001` (Kofi Mensah Boateng)                                                |
| **Student (Level 200 Eng)** | `student2`    | `password123` | Linked to Index`USTED/2024/002` (Abena Serwaa Osei)                                                  |
| **Academic Supervisor**     | `supervisor1` | `password123` | Assigned students roster and placement monitoring                                                      |

---

## Running Automated Tests

Run the full pytest suite:

```bash
pytest tests/ -v
```

Test coverage includes:

- `test_auth.py`: Authentication, session security, and role-based access restrictions.
- `test_liaison.py`: Index lookup, physical verification intake, attachment record provisioning, and letter generation.
- `test_acceptance.py`: File upload validation, MIME sniffing, and Liaison review queue.
- `test_activity_locking.py`: Mon–Fri activity logging, student locking, and server-side read-only enforcement.
- `test_pdf.py`: ReportLab byte stream generation for Introductory Letters, Acceptance Forms, Weekly Sheets, and Compiled Reports.

---

## Deployment Configuration (Render & TiDB Cloud)

1. **Web Service (Render):**
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn wsgi:app`
2. **Database (TiDB Cloud Starter / MySQL):**
   - Set environment variable:
     ```env
     DATABASE_URL=mysql+pymysql://<user>:<password>@<host>:<port>/<dbname>?ssl_ca=/etc/ssl/certs/ca-certificates.crt
     ```
3. **Durable File Storage:**
   - The `StorageService` interface isolates file persistence logic. Configure durable S3/cloud storage credentials when transitioning from local development to production.
