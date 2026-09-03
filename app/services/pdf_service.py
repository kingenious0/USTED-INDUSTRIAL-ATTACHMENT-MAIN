import io
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.qr import QrCodeWidget


class PDFService:
    """
    Generates standardized official PDFs using ReportLab according to PRD specifications:
    - Introductory Letter (Section 16)
    - Blank Physical Acceptance Form (Section 17)
    - Weekly Activity Sheet with Physical Verification Section (Section 24, 25)
    - Multi-Week Compiled Activity Document (Section 26)
    """

    @classmethod
    def _create_styles(cls):
        styles = getSampleStyleSheet()
        
        # Official USTED Brand Palette
        primary_color = colors.HexColor('#8C033B')   # Official USTED Maroon
        secondary_color = colors.HexColor('#D97706') # Official USTED Gold Accent
        text_dark = colors.HexColor('#0F172A')

        styles.add(ParagraphStyle(
            'UniversityHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            alignment=1, # Center
            textColor=primary_color
        ))
        styles.add(ParagraphStyle(
            'UnitSubHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            alignment=1,
            textColor=secondary_color
        ))
        styles.add(ParagraphStyle(
            'HeaderContact',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=colors.HexColor('#475569')
        ))
        styles.add(ParagraphStyle(
            'DocTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=15,
            alignment=1,
            textColor=primary_color
        ))
        styles.add(ParagraphStyle(
            'BodyTextDark',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=13.5,
            textColor=text_dark
        ))
        styles.add(ParagraphStyle(
            'BodyTextBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=13.5,
            textColor=text_dark
        ))
        styles.add(ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11,
            alignment=1,
            textColor=colors.whitesmoke
        ))
        styles.add(ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10.5,
            textColor=text_dark
        ))
        styles.add(ParagraphStyle(
            'TableCellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10.5,
            textColor=text_dark
        ))
        styles.add(ParagraphStyle(
            'VerificationNotice',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#B91C1C')
        ))
        return styles

    @classmethod
    def _add_letterhead(cls, story, styles, university_name="UNIVERSITY OF SKILLS TRAINING AND ENTREPRENEURIAL DEVELOPMENT"):
        story.append(Paragraph(university_name.upper(), styles['UniversityHeader']))
        story.append(Spacer(1, 2))
        story.append(Paragraph("INDUSTRIAL LIAISON & WORKPLACE EXPERIENCE LEARNING UNIT", styles['UnitSubHeader']))
        story.append(Spacer(1, 2))
        story.append(Paragraph("P.O. Box 1277, Kumasi, Ghana | Email: liaison@usted.edu.gh | Web: www.usted.edu.gh", styles['HeaderContact']))
        story.append(Spacer(1, 4))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0A2540'), spaceAfter=12))

    @classmethod
    def generate_introductory_letter(cls, attachment, letter_record, liaison_head_name=None, liaison_head_title=None, qr_access_url=None) -> bytes:
        """Generates the official standardized Introductory Letter as a PDF with embedded verification QR."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=50,
            rightMargin=50,
            topMargin=40,
            bottomMargin=40
        )
        styles = cls._create_styles()
        story = []

        cls._add_letterhead(story, styles)

        # Reference and Date Header Table
        ref_date_data = [
            [
                Paragraph(f"<b>Our Ref:</b> {letter_record.reference_number}", styles['BodyTextDark']),
                Paragraph(f"<b>Date:</b> {letter_record.letter_date.strftime('%d %B, %Y')}", styles['BodyTextDark'])
            ]
        ]
        t_ref = Table(ref_date_data, colWidths=[320, 180])
        t_ref.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(t_ref)
        story.append(Spacer(1, 14))

        # Addressee
        org_name = letter_record.addressee_organization or attachment.target_organization or "The Managing Director / HR Manager"
        story.append(Paragraph(f"<b>TO:</b><br/>{org_name}<br/>Host Organization", styles['BodyTextDark']))
        story.append(Spacer(1, 12))

        # Salutation & Subject
        story.append(Paragraph("Dear Sir/Madam,", styles['BodyTextDark']))
        story.append(Spacer(1, 8))
        story.append(Paragraph("<u><b>INTRODUCTORY LETTER FOR WORKPLACE EXPERIENCE LEARNING (WEL)</b></u>", styles['DocTitle']))
        story.append(Spacer(1, 10))

        # Student particulars table
        student = attachment.student
        commence_str = attachment.commencement_date.strftime('%d %B, %Y')
        end_str = attachment.end_date.strftime('%d %B, %Y')
        
        particulars_data = [
            [Paragraph("<b>Student Name:</b>", styles['BodyTextBold']), Paragraph(student.full_name, styles['BodyTextDark'])],
            [Paragraph("<b>Index Number:</b>", styles['BodyTextBold']), Paragraph(student.index_number, styles['BodyTextDark'])],
            [Paragraph("<b>Programme:</b>", styles['BodyTextBold']), Paragraph(student.programme, styles['BodyTextDark'])],
            [Paragraph("<b>Department:</b>", styles['BodyTextBold']), Paragraph(student.department, styles['BodyTextDark'])],
            [Paragraph("<b>Current Level:</b>", styles['BodyTextBold']), Paragraph(f"Level {student.current_level}", styles['BodyTextDark'])],
            [Paragraph("<b>Academic Year:</b>", styles['BodyTextBold']), Paragraph(attachment.academic_year, styles['BodyTextDark'])],
            [Paragraph("<b>Duration / Period:</b>", styles['BodyTextBold']), Paragraph(f"{attachment.duration_weeks} Weeks ({commence_str} to {end_str})", styles['BodyTextDark'])],
        ]
        t_particulars = Table(particulars_data, colWidths=[130, 370])
        t_particulars.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_particulars)
        story.append(Spacer(1, 12))

        # Letter Body
        body_text = (
            "We write to introduce to your reputable establishment the student whose particulars are "
            "detailed above. In partial fulfillment of the academic requirements of this University, "
            "students are required to undertake Workplace Experience Learning (industrial attachment) "
            "to acquire practical workplace competence, entrepreneurial attitude, and industry experience."
        )
        story.append(Paragraph(body_text, styles['BodyTextDark']))
        story.append(Spacer(1, 8))

        body_text2 = (
            f"We kindly request that the student be granted attachment placement in your organization "
            f"for the stipulated duration of <b>{attachment.duration_weeks} weeks</b>. During this period, "
            f"the student is expected to conform strictly to your establishment's rules, code of conduct, "
            f"and working schedule."
        )
        story.append(Paragraph(body_text2, styles['BodyTextDark']))
        story.append(Spacer(1, 8))

        body_text3 = (
            "Attached to this letter is the <b>WEL Acceptance Form</b>. If your organization is pleased to accept "
            "the student, kindly complete the Acceptance Form, endorse it with your <b>official company wet-ink stamp</b> "
            "and signature, and return it via the student."
        )
        story.append(Paragraph(body_text3, styles['BodyTextDark']))
        story.append(Spacer(1, 14))

        story.append(Paragraph("We count on your esteemed co-operation in building the nation's human capital.", styles['BodyTextDark']))
        story.append(Spacer(1, 16))

        # Signatory Section (PRD 3.0)
        signatory_name = liaison_head_name or "DONALD KWAME ASIEDU (ChPA)"
        signatory_title = liaison_head_title or "Head, Industrial Liaison Office"
        sign_block = [
            Paragraph("Yours faithfully,", styles['BodyTextDark']),
            Spacer(1, 24), # Space for wet-ink signature
            Paragraph(f"<b>{signatory_name}</b>", styles['BodyTextDark']),
            Paragraph(signatory_title, styles['BodyTextDark']),
            Paragraph("For: Vice-Chancellor", styles['BodyTextDark']),
        ]
        for item in sign_block:
            story.append(item)

        # Embedded QR Code Verification Box (Pipeline 2: 24-Hour Gateway)
        if qr_access_url:
            try:
                qr = QrCodeWidget(qr_access_url)
                b = qr.getBounds()
                w, h = b[2] - b[0], b[3] - b[1]
                scale = 55.0 / max(w, 1.0)
                d = Drawing(55, 55, transform=[scale, 0, 0, scale, 0, 0])
                d.add(qr)

                qr_cell_content = [
                    Paragraph("<b>OFFICIAL DIGITAL ONBOARDING & VERIFICATION GATEWAY</b>", styles['TableCellBold']),
                    Spacer(1, 2),
                    Paragraph(
                        "Scan this QR code using a smartphone camera within 24 hours to initiate your secure "
                        "U-IAP portal account, upload acceptance details, and access your eLogBook.",
                        styles['TableCell']
                    ),
                    Paragraph(f"<font size=6 color='#64748B'>Gateway: {qr_access_url}</font>", styles['TableCell'])
                ]

                t_qr = Table([[d, qr_cell_content]], colWidths=[65, 435])
                t_qr.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
                    ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
                    ('PADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(Spacer(1, 10))
                story.append(t_qr)
            except Exception:
                pass  # Gracefully proceed if QR generation encounters unexpected environment issue

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    @classmethod
    def generate_acceptance_form_template(cls, attachment=None) -> bytes:
        """Generates the standard physical WEL Acceptance Form template."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=35,
            bottomMargin=35
        )
        styles = cls._create_styles()
        story = []

        cls._add_letterhead(story, styles)

        story.append(Paragraph("<b>WORKPLACE EXPERIENCE LEARNING (WEL) ACCEPTANCE FORM</b>", styles['DocTitle']))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "<i>(To be completed physically by the Host Organization, signed, wet-ink stamped, and returned via student)</i>",
            styles['VerificationNotice']
        ))
        story.append(Spacer(1, 10))

        # Section A: Student Particulars
        if attachment:
            student = attachment.student
            commence_str = attachment.commencement_date.strftime('%d/%m/%Y')
            end_str = attachment.end_date.strftime('%d/%m/%Y')
            s_name = student.full_name
            s_index = student.index_number
            s_prog = student.programme
            s_level = str(student.current_level)
            s_dept = student.department
            s_acad = attachment.academic_year
            s_dur = f"{attachment.duration_weeks} Weeks"
            s_period = f"{commence_str} to {end_str}"
        else:
            s_name = "____________________________________"
            s_index = "______________________"
            s_prog = "____________________________________"
            s_level = "_______"
            s_dept = "____________________________________"
            s_acad = "2025/2026"
            s_dur = "____ Weeks"
            s_period = "____/____/2026 to ____/____/2026"

        story.append(Paragraph("<b>SECTION A: STUDENT & ATTACHMENT DETAILS (University Records)</b>", styles['BodyTextBold']))
        story.append(Spacer(1, 4))

        sec_a_data = [
            [Paragraph("<b>Student Name:</b>", styles['TableCellBold']), Paragraph(s_name, styles['TableCell']),
             Paragraph("<b>Index No:</b>", styles['TableCellBold']), Paragraph(s_index, styles['TableCell'])],
            [Paragraph("<b>Programme:</b>", styles['TableCellBold']), Paragraph(s_prog, styles['TableCell']),
             Paragraph("<b>Level:</b>", styles['TableCellBold']), Paragraph(s_level, styles['TableCell'])],
            [Paragraph("<b>Department:</b>", styles['TableCellBold']), Paragraph(s_dept, styles['TableCell']),
             Paragraph("<b>Academic Year:</b>", styles['TableCellBold']), Paragraph(s_acad, styles['TableCell'])],
            [Paragraph("<b>Duration:</b>", styles['TableCellBold']), Paragraph(s_dur, styles['TableCell']),
             Paragraph("<b>Period:</b>", styles['TableCellBold']), Paragraph(s_period, styles['TableCell'])],
        ]
        t_a = Table(sec_a_data, colWidths=[90, 180, 80, 170])
        t_a.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_a)
        story.append(Spacer(1, 12))

        # Section B: Host Organization Acceptance
        story.append(Paragraph("<b>SECTION B: HOST ORGANIZATION ACCEPTANCE (To be completed by Employer)</b>", styles['BodyTextBold']))
        story.append(Spacer(1, 4))

        sec_b_data = [
            [Paragraph("<b>1. Name of Organization:</b>", styles['TableCellBold']), Paragraph("__________________________________________________________________________", styles['TableCell'])],
            [Paragraph("<b>2. Nature of Business:</b>", styles['TableCellBold']), Paragraph("__________________________________________________________________________", styles['TableCell'])],
            [Paragraph("<b>3. Physical Location / Address:</b>", styles['TableCellBold']), Paragraph("__________________________________________________________________________", styles['TableCell'])],
            [Paragraph("<b>4. Postal Address:</b>", styles['TableCellBold']), Paragraph("__________________________________________________________________________", styles['TableCell'])],
            [Paragraph("<b>5. Telephone / Mobile:</b>", styles['TableCellBold']), Paragraph("__________________________________________________________________________", styles['TableCell'])],
            [Paragraph("<b>6. Email Address:</b>", styles['TableCellBold']), Paragraph("__________________________________________________________________________", styles['TableCell'])],
            [Paragraph("<b>7. Department Assigned:</b>", styles['TableCellBold']), Paragraph("__________________________________________________________________________", styles['TableCell'])],
            [Paragraph("<b>8. Workplace Supervisor Name:</b>", styles['TableCellBold']), Paragraph("__________________________________________________________________________", styles['TableCell'])],
            [Paragraph("<b>9. Supervisor Phone / Email:</b>", styles['TableCellBold']), Paragraph("__________________________________________________________________________", styles['TableCell'])],
            [Paragraph("<b>10. Agreed Commencement Date:</b>", styles['TableCellBold']), Paragraph("____ / ____ / 2026", styles['TableCell'])],
        ]
        t_b = Table(sec_b_data, colWidths=[160, 360])
        t_b.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_b)
        story.append(Spacer(1, 14))

        # Endorsement & Physical Stamp Area (PRD Section 17)
        story.append(Paragraph("<b>SECTION C: OFFICIAL ENDORSEMENT & WET-INK STAMP</b>", styles['BodyTextBold']))
        story.append(Spacer(1, 4))

        endorse_data = [
            [
                Paragraph(
                    "<b>Authorized Officer Endorsement:</b><br/><br/>"
                    "Name: _____________________________________<br/><br/>"
                    "Designation: ______________________________<br/><br/>"
                    "Signature: ________________________________<br/><br/>"
                    "Date: ______ / ______ / 2026",
                    styles['TableCell']
                ),
                Paragraph(
                    "<b>OFFICIAL COMPANY WET-INK STAMP</b><br/>"
                    "<i>(Mandatory: Wet-ink institutional stamp must be applied below)</i><br/><br/><br/><br/><br/><br/>",
                    styles['TableCell']
                )
            ]
        ]
        t_endorse = Table(endorse_data, colWidths=[270, 250])
        t_endorse.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#0A2540')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94A3B8')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#FAFAFA')),
        ]))
        story.append(t_endorse)
        story.append(Spacer(1, 10))

        story.append(Paragraph(
            "<b>NOTICE TO STUDENT:</b> Once this physical form is endorsed with the official wet-ink stamp and signature, "
            "photograph or scan this document clearly and upload the file to your U-IAP portal.",
            styles['HeaderContact']
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    @classmethod
    def generate_weekly_activity_sheet(cls, weekly_activity) -> bytes:
        """
        Generates the Weekly Activity Sheet PDF with Monday-Friday activity log and
        the physical supervisor verification section (comments, signature, date, wet-ink stamp).
        Adheres strictly to PRD Section 24 & 25 and generates Landscape A4 format.
        """
        from app.documents.pdf_generator import generate_weekly_sheet_pdf
        return generate_weekly_sheet_pdf(weekly_activity.attachment_id, weekly_activity.week_number)

    @classmethod
    def generate_multi_week_compilation(cls, attachment) -> bytes:
        """
        Compiles all locked weekly records into a standardized multi-week logbook PDF.
        Adheres strictly to PRD Section 26.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=35,
            rightMargin=35,
            topMargin=30,
            bottomMargin=30
        )
        styles = cls._create_styles()
        story = []

        cls._add_letterhead(story, styles)

        student = attachment.student
        story.append(Paragraph("<b>COMPILED WORKPLACE EXPERIENCE LEARNING (WEL) LOGBOOK</b>", styles['DocTitle']))
        story.append(Spacer(1, 6))

        # Cover Summary Box
        summary_data = [
            [Paragraph("<b>Student Name:</b>", styles['TableCellBold']), Paragraph(student.full_name, styles['TableCell']),
             Paragraph("<b>Index Number:</b>", styles['TableCellBold']), Paragraph(student.index_number, styles['TableCell'])],
            [Paragraph("<b>Programme:</b>", styles['TableCellBold']), Paragraph(student.programme, styles['TableCell']),
             Paragraph("<b>Department:</b>", styles['TableCellBold']), Paragraph(student.department, styles['TableCell'])],
            [Paragraph("<b>Host Organization:</b>", styles['TableCellBold']), Paragraph(attachment.target_organization or "N/A", styles['TableCell']),
             Paragraph("<b>Academic Year:</b>", styles['TableCellBold']), Paragraph(attachment.academic_year, styles['TableCell'])],
            [Paragraph("<b>Duration:</b>", styles['TableCellBold']), Paragraph(f"{attachment.duration_weeks} Weeks", styles['TableCell']),
             Paragraph("<b>Status:</b>", styles['TableCellBold']), Paragraph(attachment.status.upper(), styles['TableCell'])],
        ]
        t_sum = Table(summary_data, colWidths=[100, 160, 95, 170])
        t_sum.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_sum)
        story.append(Spacer(1, 10))

        story.append(Paragraph(
            "<b>Note on Institutional Integrity:</b> This compiled document represents the digital record of weekly entries "
            "and corresponding physical verification sections. Official physical assessment forms (20-item) and confidential "
            "supervisor evaluations remain sealed physical academic artifacts.",
            styles['HeaderContact']
        ))
        story.append(Spacer(1, 14))

        # Weeks Loop
        weeks = list(attachment.weekly_activities)
        if not weeks:
            story.append(Paragraph("<i>No weekly activity logs recorded for this attachment.</i>", styles['BodyTextDark']))
        else:
            for idx, week in enumerate(weeks):
                if idx > 0:
                    story.append(PageBreak())
                    cls._add_letterhead(story, styles)

                start_str = week.start_date.strftime('%d/%m/%Y')
                end_str = week.end_date.strftime('%d/%m/%Y')
                lock_text = f"LOCKED ({week.locked_at.strftime('%d/%m/%Y')})" if week.is_locked else "UNLOCKED / DRAFT"

                story.append(Paragraph(f"<b>WEEK {week.week_number} ({start_str} - {end_str}) — {lock_text}</b>", styles['DocTitle']))
                story.append(Spacer(1, 6))

                table_data = [
                    [
                        Paragraph("<b>Day / Date</b>", styles['TableHeader']),
                        Paragraph("<b>Hours</b>", styles['TableHeader']),
                        Paragraph("<b>Key Tasks & Learning Outcomes</b>", styles['TableHeader']),
                        Paragraph("<b>Skills Demonstrated / Remarks</b>", styles['TableHeader'])
                    ]
                ]

                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                for day in days:
                    entry = week.get_entry_for_day(day)
                    date_str = entry.date.strftime('%d/%m') if entry else ""
                    day_label = f"<b>{day}</b><br/>{date_str}"
                    hours_str = f"{entry.start_time or ''} - {entry.end_time or ''}" if (entry and (entry.start_time or entry.end_time)) else "—"
                    tasks_str = entry.key_tasks if (entry and entry.key_tasks) else "<i>No entry</i>"
                    skills_str = entry.skills_demonstrated if (entry and entry.skills_demonstrated) else "—"

                    table_data.append([
                        Paragraph(day_label, styles['TableCell']),
                        Paragraph(hours_str, styles['TableCell']),
                        Paragraph(tasks_str, styles['TableCell']),
                        Paragraph(skills_str, styles['TableCell'])
                    ])

                t_w = Table(table_data, colWidths=[75, 65, 230, 155])
                t_w.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A2540')),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('PADDING', (0, 0), (-1, -1), 3),
                ]))
                story.append(t_w)
                story.append(Spacer(1, 8))

                # Verification Box
                verif_data = [
                    [
                        Paragraph(
                            "<b>Supervisor Comments:</b> ____________________________________________________________________<br/>"
                            "Signature: _______________________ Date: _____ / _____ / 2026",
                            styles['TableCell']
                        ),
                        Paragraph("<b>Company Wet-Ink Stamp Area</b><br/><br/><br/>", styles['TableCell'])
                    ]
                ]
                t_v = Table(verif_data, colWidths=[355, 170])
                t_v.setStyle(TableStyle([
                    ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#0A2540')),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94A3B8')),
                    ('PADDING', (0, 0), (-1, -1), 4),
                    ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#FAFAFA')),
                ]))
                story.append(KeepTogether([t_v]))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    @classmethod
    def generate_confidential_assessment_form(cls, attachment=None) -> bytes:
        """
        Generates the official 2-page Confidential 20-Item Assessment Form
        for Host Organization Industry Supervisors per PRD 3.0.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=30,
            bottomMargin=30
        )
        styles = cls._create_styles()
        story = []

        # =========================================================================
        # PAGE 1: Particulars & Categories 1 & 2
        # =========================================================================
        cls._add_letterhead(story, styles)

        story.append(Paragraph("<b>CONFIDENTIAL WORKPLACE SUPERVISOR ASSESSMENT FORM</b>", styles['DocTitle']))
        story.append(Spacer(1, 2))
        story.append(Paragraph(
            "<i>(STRICTLY CONFIDENTIAL: To be completed solely by the Industry Supervisor at the conclusion of the attachment. "
            "Scores must reflect objective workplace performance. Stamp and sign in Section D.)</i>",
            styles['VerificationNotice']
        ))
        story.append(Spacer(1, 6))

        # Section A: Trainee Particulars
        if attachment:
            student = attachment.student
            commence_str = attachment.commencement_date.strftime('%d/%m/%Y')
            end_str = attachment.end_date.strftime('%d/%m/%Y')
            s_name = student.full_name
            s_index = student.index_number
            s_prog = student.programme
            s_level = f"Level {student.current_level}"
            s_org = attachment.target_organization or "____________________________________"
            s_period = f"{commence_str} to {end_str} ({attachment.duration_weeks} Wks)"
        else:
            s_name = "____________________________________"
            s_index = "______________________"
            s_prog = "____________________________________"
            s_level = "_______"
            s_org = "____________________________________"
            s_period = "____/____/2026 to ____/____/2026"

        sec_a_data = [
            [Paragraph("<b>Student Name:</b>", styles['TableCellBold']), Paragraph(s_name, styles['TableCell']),
             Paragraph("<b>Index Number:</b>", styles['TableCellBold']), Paragraph(s_index, styles['TableCell'])],
            [Paragraph("<b>Programme:</b>", styles['TableCellBold']), Paragraph(s_prog, styles['TableCell']),
             Paragraph("<b>Level:</b>", styles['TableCellBold']), Paragraph(s_level, styles['TableCell'])],
            [Paragraph("<b>Host Establishment:</b>", styles['TableCellBold']), Paragraph(s_org, styles['TableCell']),
             Paragraph("<b>Attachment Period:</b>", styles['TableCellBold']), Paragraph(s_period, styles['TableCell'])],
        ]
        t_a = Table(sec_a_data, colWidths=[105, 175, 95, 145])
        t_a.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 3.5),
        ]))
        story.append(t_a)
        story.append(Spacer(1, 8))

        # Section B Rubric Header
        story.append(Paragraph(
            "<b>SECTION B: PERFORMANCE EVALUATION RUBRIC (20 OBJECTIVE METRICS — 100 POINTS TOTAL)</b>",
            styles['BodyTextBold']
        ))
        story.append(Paragraph(
            "Rating Scale: <b>5</b> = Excellent (Outstanding) | <b>4</b> = Very Good (Above Average) | "
            "<b>3</b> = Satisfactory (Competent) | <b>2</b> = Fair (Needs Improvement) | <b>1</b> = Unsatisfactory (Poor)",
            styles['TableCell']
        ))
        story.append(Spacer(1, 4))

        def _build_category_table(title, items, start_num):
            cat_rows = [
                [Paragraph(f"<b>{title}</b>", styles['TableHeader']),
                 Paragraph("<b>5</b>", styles['TableHeader']),
                 Paragraph("<b>4</b>", styles['TableHeader']),
                 Paragraph("<b>3</b>", styles['TableHeader']),
                 Paragraph("<b>2</b>", styles['TableHeader']),
                 Paragraph("<b>1</b>", styles['TableHeader'])]
            ]
            for i, text in enumerate(items):
                num = start_num + i
                cat_rows.append([
                    Paragraph(f"<b>{num}.</b> {text}", styles['TableCell']),
                    Paragraph("[ &nbsp; ]", styles['TableCell']),
                    Paragraph("[ &nbsp; ]", styles['TableCell']),
                    Paragraph("[ &nbsp; ]", styles['TableCell']),
                    Paragraph("[ &nbsp; ]", styles['TableCell']),
                    Paragraph("[ &nbsp; ]", styles['TableCell']),
                ])
            cat_table = Table(cat_rows, colWidths=[370, 30, 30, 30, 30, 30])
            cat_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8C033B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 2.5),
            ]))
            return cat_table

        # Category 1
        cat1_items = [
            "Punctuality, regularity of attendance, and adherence to official reporting hours",
            "Compliance with workplace health, safety rules, and organizational regulations",
            "Professional appearance, appropriate grooming, and strict dress code conformity",
            "Respect for workplace hierarchy, organizational protocol, and fellow workers",
            "General dependability, reliability, and responsibility in handling duties",
        ]
        story.append(_build_category_table("CATEGORY 1: WORK ATTITUDE & PROFESSIONAL CONDUCT (25%)", cat1_items, 1))
        story.append(Spacer(1, 6))

        # Category 2
        cat2_items = [
            "Comprehension and practical application of theoretical classroom knowledge",
            "Proficiency and care in operating workplace tools, machinery, or digital equipment",
            "Precision, accuracy, and overall quality of daily technical output produced",
            "Efficiency, time management, and ability to meet agreed operational deadlines",
            "Adaptability to technical changes, emerging workflows, and new work methods",
        ]
        story.append(_build_category_table("CATEGORY 2: TECHNICAL COMPETENCE & EXECUTION (25%)", cat2_items, 6))

        # =========================================================================
        # PAGE 2: Categories 3 & 4, Scoring Box, Qualitative Assessment, Wet-Ink Stamp
        # =========================================================================
        story.append(PageBreak())

        # Category 3
        cat3_items = [
            "Clarity, conciseness, and professionalism in spoken/verbal communications",
            "Quality, neatness, and accuracy in keeping written notes and technical records",
            "Ability to listen attentively and accurately execute multi-step instructions",
            "Teamwork, active cooperation, and positive engagement with coworkers",
            "Openness to guidance, supervisory mentoring, and constructive correction",
        ]
        story.append(_build_category_table("CATEGORY 3: INTERPERSONAL COMMUNICATION & TEAM DYNAMICS (25%)", cat3_items, 11))
        story.append(Spacer(1, 6))

        # Category 4
        cat4_items = [
            "Resourcefulness, initiative, and proactive attitude in solving practical problems",
            "Readiness to ask clarifying questions and seek appropriate guidance when needed",
            "Enthusiasm, intellectual curiosity, and eagerness to acquire new competencies",
            "Ability to propose valuable improvements to workplace processes or productivity",
            "Capacity for sustained independent work under minimal direct supervision",
        ]
        story.append(_build_category_table("CATEGORY 4: INITIATIVE, ADAPTABILITY & PROBLEM SOLVING (25%)", cat4_items, 16))
        story.append(Spacer(1, 8))

        # Scoring Calculation & Grade Scale Box
        score_data = [
            [
                Paragraph("<b>SCORE CALCULATION & GRADE CONVERSION (Max: 100 Marks)</b>", styles['TableCellBold']),
                Paragraph("<b>Grading Scale:</b> 80-100: A | 70-79: B | 60-69: C | 50-59: D | Below 50: F", styles['TableCell'])
            ],
            [
                Paragraph(
                    "<b>Total Points Scored:</b> &nbsp; [ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ] / 100 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
                    "<b>Final Grade:</b> &nbsp; [ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ]",
                    styles['TableCellBold']
                ),
                Paragraph("<i>(Passing mark is 50%. Evaluator signature required below)</i>", styles['TableCell'])
            ]
        ]
        t_score = Table(score_data, colWidths=[310, 210])
        t_score.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#0F172A')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_score)
        story.append(Spacer(1, 8))

        # Section C: Industry Supervisor Qualitative Assessment
        story.append(Paragraph("<b>SECTION C: INDUSTRY SUPERVISOR QUALITATIVE REMARKS</b>", styles['BodyTextBold']))
        story.append(Spacer(1, 3))
        qual_data = [
            [Paragraph("<b>Notable Strengths & Talents Observed:</b><br/><br/>__________________________________________________________________________________________________", styles['TableCell'])],
            [Paragraph("<b>Areas Needing Further Academic / Practical Improvement:</b><br/><br/>__________________________________________________________________________________________________", styles['TableCell'])],
            [Paragraph(
                "<b>Employment / Retention Prospect:</b> &nbsp;&nbsp; "
                "[ &nbsp; ] Strongly Recommended &nbsp;&nbsp;&nbsp;&nbsp; "
                "[ &nbsp; ] Recommended &nbsp;&nbsp;&nbsp;&nbsp; "
                "[ &nbsp; ] Recommended with Reservations &nbsp;&nbsp;&nbsp;&nbsp; "
                "[ &nbsp; ] Not Recommended",
                styles['TableCell']
            )],
        ]
        t_qual = Table(qual_data, colWidths=[520])
        t_qual.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFFFFF')),
        ]))
        story.append(t_qual)
        story.append(Spacer(1, 8))

        # Section D: Endorsement & Mandatory Wet-Ink Stamp Box (PRD Section 17 & 25)
        story.append(Paragraph("<b>SECTION D: AUTHENTICATION & MANDATORY WET-INK STAMP</b>", styles['BodyTextBold']))
        story.append(Spacer(1, 3))

        endorse_data = [
            [
                Paragraph(
                    "<b>Industry Evaluator Details:</b><br/><br/>"
                    "Supervisor Name: _________________________________________<br/><br/>"
                    "Designation / Title: ______________________________________<br/><br/>"
                    "Direct Telephone: _________________________________________<br/><br/>"
                    "Signature: ______________________ Date: ____/____/2026",
                    styles['TableCell']
                ),
                Paragraph(
                    "<b>MANDATORY OFFICIAL COMPANY WET-INK STAMP</b><br/>"
                    "<i>(Box: &ge; 60mm &times; 35mm. Must apply official ink seal below)</i><br/><br/><br/><br/><br/><br/>",
                    styles['TableCell']
                )
            ]
        ]
        t_endorse = Table(endorse_data, colWidths=[310, 210])
        t_endorse.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#8C033B')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t_endorse)

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
