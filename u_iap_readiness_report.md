# U-IAP DEVELOPMENT READINESS REPORT

**Project:** USTED Industrial Attachment Management System (U-IAP)  
**Phase:** Phase 0 — Repository Inspection & Readiness Assessment  
**Target Directory:** `USTED INDUSTRIAL ATTACHMENT(U-IAP MAIN)`  
**Document Version:** 1.0  
**Target Readiness:** October–November 2026  

---

## A. Current System (What Already Exists)

1. **Root Workspace Inspection:**
   - Workspace path: `c:\Users\kinge\My-ReactNewApp\USTED Industrial Attachment Portal`
   - Subdirectories present:
     - `USTED INDUSTRIAL ATTACHMENT(U-IAP MAIN)`: The target folder designated for the U-IAP core system. Initialized and established with Python + Flask + SQLAlchemy + ReportLab architecture.
     - `USTED_U_IAP`: Contains an Expo / React Native project (the separate student eLogSheet / mobile application).
     - `usted-uiap-web`: Contains an existing Next.js web application.
2. **U-IAP Core Status:**
   - The core system is now established in `USTED INDUSTRIAL ATTACHMENT(U-IAP MAIN)` from the approved PRD using Python + Flask + Jinja2 + ReportLab.
   - The existing eLogSheet is a separate student activity logger and is not absorbed or rewritten now. Clean REST endpoints (`/api/v1/...`) are provided for future integration.
3. **Environment:**
   - Python 3.12.10 and Pip 25.0.1 with isolated virtual environment in `venv/`.

---

## B. Confirmed Requirements

1. **Student Verification & Intake:**
   - Physical Liaison Office visit is mandatory.
   - Officer looks up students by University Index Number in the Student Master Data.
   - Levels 100, 200, 300, and 400 are all supported (no hardcoded Level 300 restriction).
   - Students voluntarily undertake WEL; multiple attachments across different periods are supported.
2. **Document Engine (ReportLab):**
   - Official Introductory Letter generated as a standardized PDF with reference numbers, student parameters, and authorized signatory line.
   - Blank physical Acceptance Form generated/downloadable.
   - Weekly Activity Sheet generated after student locks the week. Must include physical supervisor verification section (supervisor comments, signature, verification date, and official company wet-ink stamp).
   - Multi-week compiled logbook PDF.
3. **Acceptance Form Upload & Review:**
   - Student scans/photographs the physically stamped/signed Acceptance Form and uploads it (PDF, JPEG, PNG supported).
   - Server-side validation of file type, MIME sniffing, and size constraints.
   - Liaison review queue allows approving or flagging blurry/incomplete submissions.
4. **Activity Logger & Student Locking:**
   - Monday through Friday daily entries (Date, Start Time, End Time, Key Tasks / Learning Outcomes, Skills Demonstrated, Remarks).
   - Expandable text fields without artificial 2–3 line constraints.
   - Student controls when the week is locked (NO automatic Friday or time-based locks).
   - Once locked, the server strictly enforces read-only access (no student edits or deletions).
5. **Physical Preservation:**
   - Physical wet-ink company stamps, physical supervisor signatures, and physical 20-item sealed assessment forms are strictly preserved.
   - No fake digital stamps, no digital company accounts, and no student-facing assessment scoring workflows.
6. **Audit Trail & RBAC:**
   - Roles: Student, Liaison Officer, Liaison Head / Unit Admin, Academic Supervisor.
   - Audit logging for all critical events (attachment creation, letter generation, acceptance upload, review, weekly lock, document generation).

---

## C. Requirements Corrections Applied

1. **Separation from eLogSheet:** Clarified that the existing eLogSheet is an external student activity logger and is not the U-IAP core system. Clean REST endpoints (`/api/v1/...`) are exposed for future integration without coupling core business logic.
2. **Acceptance Workflow Configuration (OQ-04):** Rather than hardcoding whether logging requires prior Liaison approval (Option A) or allows logging while review occurs asynchronously (Option B), the system implements a runtime configuration toggle `REQUIRE_ACCEPTANCE_APPROVAL_BEFORE_LOGGING`.
3. **No Automatic Locking:** Clarified that weekly locking is explicitly student-controlled.
4. **Physical Verification Retention:** Refactored weekly PDF generation to guarantee official wet-ink stamp and signature capture zones.

---

## D. Existing Implementation Gaps

All initial core architectural components have been implemented:
1. Complete Flask application architecture with application factory pattern.
2. SQLAlchemy models and database abstraction (SQLite local, TiDB/MySQL remote).
3. Abstract `StorageService` with local filesystem implementation and cloud storage contract.
4. ReportLab PDF generation engine for Introductory Letters, Blank Acceptance Forms, Weekly Activity Sheets, and Multi-Week Compilation.
5. Role-based authentication system with secure session management.
6. Server-side validation and CSRF protection.
7. Responsive, university-branded HTML5/CSS3/Vanilla JS interface.
8. REST API endpoints for external eLogSheet integration.
9. Automated test suite for all business rules and security constraints.

---

## E. Critical Risks & Mitigation Strategies

1. **Storage Ephemerality on Render (Hosting Risk):**
   - *Risk:* Render free tier local filesystem is ephemeral; uploaded scans would be lost on container restart.
   - *Mitigation:* Abstract `StorageService` interface isolates file storage logic, enabling smooth zero-code-change transition to durable S3/cloud storage in staging/production.
2. **Database Free Tier Throttling (TiDB Cloud):**
   - *Risk:* Request unit or storage exhaustion on free-tier database.
   - *Mitigation:* Keep queries lean, index critical lookup columns (`index_number`, `attachment_id`, `user_id`), and never store raw binary files directly in the database.
3. **Premature Policy Invention:**
   - *Risk:* Silently choosing an institutional rule that has not been confirmed.
   - *Mitigation:* Strict adherence to PRD Rule 3. Unresolved questions (OQ-01 through OQ-12) are represented as configuration options or clear operational states.

---

## F. MVP Scope (November Readiness Baseline)

- **Authentication & RBAC:** Student, Liaison Officer, Liaison Head, Academic Supervisor.
- **Student Master Data:** Search and lookup by University Index Number (Levels 100–400).
- **Liaison Office Intake:** In-person student verification and attachment creation.
- **Introductory Letter Engine:** Standardized ReportLab PDF generation with reprint tracking.
- **Acceptance Form Generation & Ingestion:** Blank form download, scan upload (PDF/JPG/PNG), server-side validation, and Liaison review queue.
- **Student Dashboard & Monday–Friday Activity Logger:** Clean expandable fields, autosave, student-controlled locking, server-side immutable lock enforcement.
- **Weekly Activity Sheet Generation:** PDF with physical supervisor signature and wet-ink stamp boxes.
- **Multi-Week Compilation:** End-of-attachment consolidated PDF.
- **Liaison & Admin Dashboards:** Active attachment monitoring, review queues, audit log viewer.
- **Security & Audit Trail:** CSRF, password hashing, session security, detailed audit logs.
- **Automated Tests:** Comprehensive test coverage for auth, locking, uploads, and lifecycle.

---

## G. Open Institutional Questions (Documented)

- **OQ-01 (Student Master Source):** Supported via CSV/Excel seed ingestion and database records.
- **OQ-02 (Multiple Attachments):** 1:M relationship between `StudentMaster` and `AttachmentRecord` supported.
- **OQ-03 (Authentication Standard):** Standalone secure U-IAP credentials implemented; extensible for future university SSO.
- **OQ-04 (Acceptance Status Governance):** Configurable toggle between Option A (approval required before logging) and Option B (asynchronous review).
- **OQ-05 (Administrative Unlock):** Lock status recorded with actor and timestamp; unlock capability restricted to administrative exception procedure.
- **OQ-06 (Weekend Activities):** Left unassumed as per PRD; standard logger models Monday–Friday.
- **OQ-07 (Duration):** Configurable per attachment record (e.g. 6, 8, 12 weeks).
- **OQ-08 & OQ-09 (Technical Report & Assessment):** Preserved as physical deliverables.

---

## H. Recommended Development Sequence

1. **Phase 1: Project Foundation & Architecture** (Structure, Flask app factory, config, models, database abstraction, storage service) — **Completed**.
2. **Phase 2: Master Data & Liaison Intake** (Index lookup, physical verification, attachment creation) — **Completed**.
3. **Phase 3: Document Engine (ReportLab)** (Introductory Letter & Acceptance Form templates) — **Completed**.
4. **Phase 4: Acceptance Upload & Review Queue** (Validation, storage, Liaison review) — **Completed**.
5. **Phase 5: Activity Logger & Student Locking** (Mon-Fri fields, expandable UI, server-side lock enforcement) — **Completed**.
6. **Phase 6: Weekly Sheet & Multi-Week PDF Generation** (Physical verification sections) — **Completed**.
7. **Phase 7: Monitoring, Audit Trail & eLogSheet REST API** (Dashboards, audit viewer, API endpoints) — **Completed**.
8. **Phase 8: Automated Verification & Testing** (Pytest suite, manual workflow verification) — **In Progress**.
