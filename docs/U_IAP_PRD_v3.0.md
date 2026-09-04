Product Requirements Document (PRD 3.0)
**System Title:** USTED Industrial Attachment Management System (U-IAP) & eLogBook Integration Ecosystem
**Target Institution:** University of Skills Training and Entrepreneurial Development (USTED), Kumasi, Ghana
**Operating Unit:** Industrial Liaison & Workplace Experience Learning (WEL) Unit
**Architecture:** Hybrid Physical-Digital Portal with Zonal Field Supervision & SSO External Integration
**Document Status:** Approved for Production Engineering & Audit Compliance

---

## 1. Executive Summary & Problem Domain

### 1.1 The Operational Context

The Industrial Liaison Unit at USTED coordinates mandatory and voluntary Workplace Experience Learning (WEL) across all degree levels (100–400). Historically, this process suffered from severe administrative bottlenecks:

- **Terminal Congestion:** Thousands of students crowded the physical Liaison Office at the end of each semester to collect paper letters and forms.
- **Forged Placement Risks:** Past administrative loopholes allowed non-students to forge placement papers or misrepresent institutional backing.
- **Paper Waste & Information Loss:** Students relied on loose, photocopied paper activity sheets that offered inadequate space for technical write-ups and frequently went missing before final grading.
- **Blind Supervisory Logistics:** Liaison Officers tracked company locations via unstructured forms and manual mapping, leaving lecturers without coordinates, phone numbers, or structured routes during supervisory monitoring tours.
- **Volatile Calendar Durations:** Institutional shifts frequently compressed attachment periods from standard lengths down to 5 or 6 weeks, breaking rigid systems that assumed an immutable 8-week duration.

### 1.2 The U-IAP Solution

U-IAP 3.0 establishes an institutional ecosystem that bridges physical authentication (wet-ink company stamps, signed envelopes) with a digital lifecycle:

1. **Dual Intake Engine:** Enables both assisted walk-in desk registration and online self-service while enforcing identity validation against an institutional master dataset.
2. **Dynamic ReportLab PDF Engine:** Produces institutional placement letters bearing official signatories and 24-hour smart QR authentication codes.
3. **Geo-Zonal Supervisory Hub:** Captures Ghana Post Digital Addresses (`AK-039-2345`), landmark notes, and GPS coordinates to automate lecturer route allocation with turn-by-turn navigation.
4. **Resilient Decoupled Architecture:** Pairs a secure Flask/SQLAlchemy management core on Render with a high-performance web/mobile eLogBook application on Vercel.

---

## 2. Institutional Brand Tokens & UI Design Standards

### 2.1 Strict Non-"AI-istic" Frontend Directive

Even though rapid development tools (such as Claude Code, Cursor, Windsurf, AntiGravity) are leveraged to accelerate scaffolding, the resulting User Interface must **NEVER** look generic, hyper-stylized, or "AI-generated."

- **No AI Clichés:** Strictly prohibit excessive glowing glassmorphism, hyper-saturated neon gradients, floating blur orbs, decorative purple drop shadows, or generic marketing dashboard illustrations.
- **Institutional Realism:** The UI must resemble an enterprise-grade Ghanaian tertiary portal (akin to academic registry systems, GOV.UK design standards, or Tabler ERPs).
- **Dense, Functional Layouts:** Focus on clean information hierarchy, clear contrast, high readability under sunlight, sharp table borders (`border-slate-200`), and structured form controls.
- **Predictable Navigation:** Standard top navigation, simple card outlines, legible monospaced badges, and standard tabular layouts instead of whimsical decorative components.

### 2.2 Official Institutional Color Palette

- **Primary Maroon:** `#8C033B` (Brand identity, primary action buttons, borders, table accents)
- **Header Deep Maroon:** `#6B022D` (Top global navigation, table headers, document banners)
- **Accent Gold:** `#D97706` (Secondary actions, warning badges, notification callouts)
- **Light Gold Tone:** `#FEF3C7` (Badge backgrounds, alert card accents)
- **Slate Dark:** `#0F172A` (Typography, deep structural containers)
- **Canvas Soft Neutral:** `#F8FAFC` (Page background)
- **Verified Green:** `#15803D` (Approved statuses, successful sync badges)

### 2.3 Mobile Responsiveness Standards

- **Shell Architecture:** `layout-boxed` container via Tabler Core CSS (`@tabler/core@latest`).
- **Mobile Navigation:** Collapsible navbar converting to an off-canvas drawer on viewports $< 1024\text{px}$.
- **Input Sizing:** All `<input>` and `<select>` controls enforce a minimum height of $44\text{px}$ and font size of $16\text{px}$ to prevent iOS Safari auto-zooming.
- **Touch Elements:** All action buttons and clickable table cells maintain a minimum hit-target of $48\text{px} \times 48\text{px}$.

---

## 3. System Actors & Role-Based Permissions (RBAC)

| Role                               | Operational Scope & Capabilities                                                                                                                                                                             |
| :--------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Student**                        | Self-initiates placement; downloads official placement letters, blank acceptance forms, and assessment matrices; uploads endorsed acceptance scans; captures workplace GPS pins; launches external eLogBook. |
| **Liaison Officer**                | Conducts walk-in student search; registers missing students on the fly; configures cycle parameters; audits uploaded acceptance forms for wet-ink stamps; groups students by region.                         |
| **Academic Supervisor (Lecturer)** | Views assigned students filtered by zone/region; accesses company digital addresses and GPS coordinates; launches Google Maps navigation; records supervisory visit logs.                                    |
| **System Administrator**           | Manages global settings (academic year, variable week duration); uploads master student datasets; inspects audit trails and system logs.                                                                     |

---

## 4. End-to-End Operational Lifecycle Pipelines

## ┌────────────────────────────────────────────────────────┐│ PIPELINE 1: INTAKE & LETTER GENERATION ││ Dual Intake: Liaison Walk-In OR Online Self-Service │└───────────────────────────┬────────────────────────────┘│▼┌────────────────────────────────────────────────────────┐│ PIPELINE 2: SMART QR PORTAL ONBOARDING ││ 24-Hour Timed Token -> Account Activation -> Mobile │└───────────────────────────┬────────────────────────────┘│▼┌────────────────────────────────────────────────────────┐│ PIPELINE 3: PLACEMENT INGESTION & GEOLOCATION ││ Ghana Post GPS + Pin Coordinates + Wet-Ink Scan │└───────────────────────────┬────────────────────────────┘│▼┌────────────────────────────────────────────────────────┐│ PIPELINE 4: ZONAL SUPERVISION & MAPPING ││ Regional Clustering -> Lecturer Allocation -> Maps Nav│└───────────────────────────┬────────────────────────────┘│▼┌────────────────────────────────────────────────────────┐│ PIPELINE 5: DIGITAL eLOGBOOK (EXTERNAL SSO) ││ Single Sign-On -> Mon-Fri Activity Logging -> Lock │└───────────────────────────┬────────────────────────────┘│▼┌────────────────────────────────────────────────────────┐│ PIPELINE 6: CLOSEOUT & PHYSICAL EVALUATION ││ Landscape A4 Verification + Sealed 20-Item Envelope │└────────────────────────────────────────────────────────┘

### Pipeline 1: Intake & Letter Generation (Dual-Track Model)

#### Track A: Assisted Walk-in Intake (Liaison Counter)

1. The student visits the Liaison Office with their Student ID Card.
2. The Liaison Officer enters the Index Number (e.g., `5230100452`) at `/liaison/student-lookup`.
3. If the student exists in `StudentMaster`, their full details auto-populate. If missing, the officer clicks `+ Register New Student` to persist their record immediately.
4. The officer inputs the target organization name and dates, then triggers document generation.
5. The system generates the **Official Introductory Letter (PDF)** bearing:
   - Header: `UNIVERSITY OF SKILLS TRAINING AND ENTREPRENEURIAL DEVELOPMENT (USTED)`
   - Authorized Signatory: `DONALD KWAME ASIEDU (ChPA), SENIOR ASSISTANT REGISTRAR (INDUSTRIAL LIAISON OFFICE) FOR: REGISTRAR`
   - Dynamic 24-hour smart QR code linking to the onboarding gateway.
6. The officer prints the letter and hands it to the student. The officer does not print blank acceptance or assessment forms.

#### Track B: Remote Online Self-Service Intake

1. The student accesses the portal at `/auth/register`.
2. The student enters their Index Number.
3. The system checks `StudentMaster`. If not found, access is refused with instructions to contact the Liaison Unit. If found, their Name, Programme, and Department lock into place as read-only attributes.
4. The student sets their password and provides their Ghanaian mobile number.
5. In their newly opened workspace, the student enters the company name and clicks **Generate Official Letter**. The PDF compiles on the fly with the dynamic QR code and becomes immediately downloadable.

---

### Pipeline 2: Smart QR Gateway & Student Onboarding

To prevent unauthorized document generation, the system validates all QR interactions using signed tokens.

                STUDENT SCANS QR CODE ON LETTER
                               │
                               ▼
         GET /portal/access/<index_number>?token=<token></token>
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
    [Token Valid (< 24h)]            [Token Expired / Invalid]
                │                             │
    ┌───────────┴───────────┐                 ▼
    ▼                       ▼            Redirect to /auth/login

[Account Not Activated] [Account Exists] "Token expired. Please sign in."│ │▼ ▼Redirect to /auth/activate Redirect to /auth/login(Pre-filled Name & Index) (Pre-filled Index Number)

#### Verification Rules:

- Tokens use `itsdangerous.URLSafeTimedSerializer` with a strict `max_age=86400` (24 hours).
- The phone number must pass the Ghanaian mobile regex `^(?:\+233|233|0)(20|23|24|25|26|27|28|50|53|54|55|56|57|59)\d{7}$` and normalize to E.164 format (`+233...`).

---

### Pipeline 3: Placement Ingestion, Geolocation, & Endorsement Audit

1. **Company Intake:** The student presents their introductory letter to the host organization.
2. **Document Retrieval:** From the **Self-Service Document Hub** on their dashboard, the student downloads the blank **WEL Acceptance Form (PDF)** and prints it.
3. **Physical Endorsement:** The company completes Part II, adding the workplace supervisor's signature and the **official company wet-ink stamp**.
4. **Digital Submission:** On the mobile portal, the student enters:
   - Company Official Name & Industry Sector (Private, Public, NGO, Statutory).
   - Workplace Supervisor Name & Verified Telephone.
   - **Ghana Post Digital Address:** Format-validated to standard alphanumeric syntax (e.g., `AK-039-2345`).
   - **Physical Landmark:** Notable geographic point (e.g., "Adjacent Shell Station, Harper Road").
   - **Exact Pin Coordinates:** The student taps `[ 📍 Capture Current Pin ]`, prompting the browser Geolocation API to record latitude and longitude.
   - **Endorsed Scan Upload:** Uploads a photo or PDF of the stamped document (max 5MB, strictly MIME-sniffed).
5. **Liaison Verification:** The submission enters the review queue at `/liaison/acceptance-queue`. The officer inspects the scan for a legitimate wet-ink stamp. Once approved, the attachment updates to `logging_active`.

---

### Pipeline 4: Zonal Field Supervision & Navigation Hub

This pipeline replaces manual location tracking by grouping students automatically:

[Approved Acceptance Records with Regional Data]│▼/liaison/supervision/zonal-mappingFilter by: [ Ashanti Region ▼ ] [ Kumasi Metro ▼ ]│▼[Batch-Assign Lecturer: Dr. Peter Owusu]│▼LECTURER PORTAL VIEW• Student: Elliot Paakow Entsiwah (5230100452)• Company: GRIDCo Kumasi Area Office• Address: AK-039-2345 (Behind ECG Substation)• Contacts: Student (0244123456) | Supervisor (0201234567)• Actions:[ 🗺️ Open in Google Maps ] ──► Launches Turn-by-Turn GPS Directions[ 📝 Log Supervisory Visit ] ──► Submits Official Field Visit Notes

- **Dynamic Navigation URLs:**
  - If GPS coordinates exist: `https://www.google.com/maps/dir/?api=1&destination={latitude},{longitude}`
  - If coordinates are missing: `https://www.google.com/maps/search/?api=1&query={organization}+{location}+Ghana`

---

### Pipeline 5: External eLogBook Integration (SSO Hand-Off)

Daily activity logging is decoupled from the administrative core and hosted on a dedicated front-end application:

- **Production Host:** `https://usted-elogbook.vercel.app` (configurable via `EXTERNAL_ELOGBOOK_URL` in `.env`).
- **Authentication Hand-off:** When the student clicks **"Launch USTED eLogBook"** from their U-IAP dashboard, the system issues a signed, short-lived JWT token (`exp = time() + 120s`).
- **Payload Parameters:**
  ```json
  {
    "index_number": "5230100452",
    "full_name": "Elliot Paakow Entsiwah",
    "attachment_id": 142,
    "academic_year": "2025/2026",
    "duration_weeks": 5,
    "target_organization": "Ghana Grid Company (GRIDCo)"
  }
  ```

Daily Recording: Students log tasks Monday through Friday with expandable fields for daily duties, tools used, skills demonstrated, and operational challenges. Work auto-saves locally in the browser to prevent data loss during network drops.Pipeline 6: Closeout, Physical Verification, & Academic GradingWeekly Lock Enforcement: On Friday afternoons, the student clicks "Lock Week" in their logbook. This sets is_locked = True, making entries read-only on the server to prevent retrospective editing.Weekly Sheet Generation (ReportLab Landscape A4): The student prints their locked weekly sheet. It renders:The official institutional banner: UNIVERSITY OF SKILLS TRAINING AND ENTREPRENEURIAL DEVELOPMENT (USTED).The 5-day activity table.Ruled lines for handwritten supervisor comments.A bordered verification box measuring at least $60\text{mm} \times 35\text{mm}$, labeled AFFIX OFFICIAL COMPANY WET-INK STAMP.Physical Endorsement: The workplace supervisor reviews the tasks, writes weekly remarks, signs, and applies the physical company stamp.Confidential Assessment Form Delivery: The student downloads the official blank 2-page WEL Assessment Form (PDF) from the portal and hands it to the employer.Sealed Envelope Requirement: The workplace supervisor evaluates the student across 20 competency metrics, writes general remarks, applies the company stamp, and seals the form inside an envelope.Academic Department Hand-Off: The student delivers their compiled portfolio (stamped weekly sheets, technical report, and the sealed envelope) directly to their academic department (e.g., Department of Information Technology Education) for final grading.5. Technical Architecture & Database Schemas5.1 Technology StackCore Server: Python 3.11+ / Flask FrameworkDatabase & ORM: PostgreSQL / SQLAlchemyPDF Compilation: ReportLab Engine (in-memory byte streams)Security & Tokens: itsdangerous / PyJWT / Passlib (PBKDF2-SHA256)Frontend UI Skin: Tabler Core HTML5/CSS3 / Vanilla JavaScriptExternal Activity Logger: React / Next.js deployed on Vercel5.2 Relational Database Schema ArchitectureSQL-- 1. INSTITUTIONAL MASTER STUDENT DATASET
CREATE TABLE student_master (
id SERIAL PRIMARY KEY,
index_number VARCHAR(30) UNIQUE NOT NULL,
full_name VARCHAR(150) NOT NULL,
programme VARCHAR(150) NOT NULL,
department VARCHAR(150) NOT NULL,
current_level INTEGER NOT NULL,
phone VARCHAR(20),
email VARCHAR(120),
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. SYSTEM USERS & RBAC
CREATE TABLE users (
id SERIAL PRIMARY KEY,
username VARCHAR(50) UNIQUE NOT NULL, -- Index Number for students, staff ID for officers
email VARCHAR(120) UNIQUE NOT NULL,
password_hash VARCHAR(255) NOT NULL,
full_name VARCHAR(150) NOT NULL,
role VARCHAR(30) NOT NULL, -- 'student', 'liaison', 'supervisor', 'admin'
is_active BOOLEAN DEFAULT TRUE,
student_master_id INTEGER REFERENCES student_master(id),
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. ATTACHMENT PLACEMENT RECORDS
CREATE TABLE attachment_records (
id SERIAL PRIMARY KEY,
student_id INTEGER NOT NULL REFERENCES student_master(id),
academic_year VARCHAR(20) NOT NULL, -- e.g. '2025/2026'
duration_weeks INTEGER NOT NULL, -- Configurable: 5, 6, 8, 12 weeks
commencement_date DATE NOT NULL,
end_date DATE NOT NULL,
target_organization VARCHAR(200) NOT NULL,
organization_address VARCHAR(255),
status VARCHAR(30) NOT NULL DEFAULT 'initiated', -- 'initiated', 'pending_verification', 'logging_active', 'completed'
created_by_id INTEGER REFERENCES users(id),
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. OFFICIAL INTRODUCTORY LETTERS
CREATE TABLE placement_letters (
id SERIAL PRIMARY KEY,
attachment_id INTEGER NOT NULL REFERENCES attachment_records(id),
reference_number VARCHAR(100) UNIQUE NOT NULL, -- e.g. 'USTED/ILU/2025-2026/0001'
letter_date DATE NOT NULL,
signatory_name VARCHAR(120) DEFAULT 'DONALD KWAME ASIEDU (ChPA)',
signatory_title VARCHAR(150) DEFAULT 'SENIOR ASSISTANT REGISTRAR (INDUSTRIAL LIAISON OFFICE)',
download_count INTEGER DEFAULT 0,
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. ENDORSED ACCEPTANCE RECORDS (GEOLOCATION & AUDIT)
CREATE TABLE acceptance_records (
id SERIAL PRIMARY KEY,
attachment_id INTEGER NOT NULL REFERENCES attachment_records(id),
organization_name VARCHAR(200) NOT NULL,
organization_type VARCHAR(50) NOT NULL, -- 'Private', 'Public', 'Statutory', 'NGO'
region VARCHAR(50) NOT NULL, -- 'Ashanti', 'Greater Accra', 'Western', etc.
district_town VARCHAR(100) NOT NULL,
gps_address VARCHAR(30) NOT NULL, -- e.g. 'AK-039-2345'
landmark VARCHAR(255) NOT NULL,
latitude DOUBLE PRECISION,
longitude DOUBLE PRECISION,
supervisor_name VARCHAR(150) NOT NULL,
supervisor_phone VARCHAR(20) NOT NULL,
scan_file_path VARCHAR(255) NOT NULL,
verification_status VARCHAR(30) DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
verified_by_id INTEGER REFERENCES users(id),
verified_at TIMESTAMP WITH TIME ZONE,
rejection_reason TEXT,
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. SUPERVISORY FIELD VISITS (LECTURER AUDIT LOG)
CREATE TABLE supervision_visits (
id SERIAL PRIMARY KEY,
attachment_id INTEGER NOT NULL REFERENCES attachment_records(id),
lecturer_id INTEGER NOT NULL REFERENCES users(id),
visit_date DATE NOT NULL,
industry_supervisor_met VARCHAR(150) NOT NULL,
student_attendance_status VARCHAR(50) DEFAULT 'Present at Post',
technical_observations TEXT,
recommendations TEXT,
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
); 6. Verification and Acceptance MatrixPipeline / FeatureSuccess CriteriaFailure Mode ActionIdentity SanitizationEvery screen, badge, footer, and PDF displays USTED exclusively; all legacy strings are eliminated.Code deployment rejected if any legacy text is detected.Variable DurationAttachment records provision exactly $N$ weeks matching the admin setting (e.g., 5 weeks).Block fixed 8-week fallbacks if the calendar specifies otherwise.Anti-Fraud GatingOnly Index Numbers found in StudentMaster can activate or self-service accounts.Access denied with instructions to contact the Liaison Unit.Ghana Phone FormatValidates and normalizes phone numbers to E.164 (+233...).Form displays an error message and blocks submission on invalid input.24-Hour Smart QRScans within 24 hours route to activation or pre-filled login; expired scans show an explanation.Expired tokens route to /auth/login with an expiration alert.GPS Map RoutingLecturers can launch one-tap Google Maps directions to the student's company.Falls back to a localized Google Maps search using the Ghana Post address and town.Logbook ImmutabilityOnce locked by the student, the server returns 403 Forbidden for any update attempts.Edits are permanently blocked, and a security alert is logged.ReportLab Verification StampWeekly PDF sheets render ruled lines and a clean stamp box measuring at least $60\text{mm} \times 35\text{mm}$.PDF compilation fails if coordinate boxes overlap or text wraps improperly.Institutional AestheticInterfaces use clean Tabler cards, dense tables, and official maroon/gold; zero glowing or floating glassmorphic AI elements.Reject code/CSS styling if non-standard consumer AI styles are introduced
